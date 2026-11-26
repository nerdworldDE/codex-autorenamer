import importlib.util
import json
import os
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


RENAMER = Path(__file__).resolve().parents[1] / "codex-hooks/renamer.py"
THREAD = "018feed0-0000-7000-8000-000000000001"


class Codex:
    def __init__(self, name=None):
        self.name = name

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def call(self, method, **params):
        assert params["threadId"] == THREAD
        if method == "thread/read":
            return {"thread": {"id": THREAD, "name": self.name, "ephemeral": False}}
        if method == "thread/name/set":
            self.name = params["name"]
            return {}
        raise AssertionError(f"Unexpected RPC {method}")


class ThreadRenamerTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(RENAMER.is_file(), "The title review hook is missing")
        spec = importlib.util.spec_from_file_location("renamer", RENAMER)
        self.renamer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.renamer)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.data = Path(folder.name)
        self.codex = Codex()

    def hook(self, event, turn, **fields):
        return self.renamer.handle(
            {"hook_event_name": event, "session_id": THREAD, "turn_id": turn, **fields},
            self.data,
            lambda: self.codex,
        )

    def prompt(self, text, turn="first"):
        return self.hook("UserPromptSubmit", turn, prompt=text)

    def stop(self, text="Task answered.", turn="first", active=False):
        return self.hook("Stop", turn, last_assistant_message=text, stop_hook_active=active)

    def test_new_thread_title_follows_the_goal_on_later_turns(self):
        self.prompt("Kann Codex seinen Thread umbenennen?")
        self.assertEqual(self.stop()["decision"], "block")
        self.stop("Thread-Titel: Codex-Thread umbenennen", active=True)
        self.assertEqual(self.codex.name, "Codex-Thread umbenennen")

        self.prompt("Bitte als Skill genau so umsetzen", turn="second")
        self.assertEqual(self.stop(turn="second")["decision"], "block")
        self.stop("Thread-Titel: Codex Thread Renamer Skill", turn="second", active=True)
        self.assertEqual(self.codex.name, "Codex Thread Renamer Skill")

    def test_unknown_existing_title_requires_opt_in(self):
        self.codex.name = "Mein manueller Titel"
        self.prompt("Setze die Rückerstattungen um")
        self.assertEqual(self.stop(), {})
        self.assertEqual(self.codex.name, "Mein manueller Titel")

        self.prompt("thread-title-auto on", turn="second")
        self.assertEqual(self.stop(turn="second")["decision"], "block")
        self.stop("Thread-Titel: Stripe-Rückerstattungen", turn="second", active=True)
        self.assertEqual(self.codex.name, "Stripe-Rückerstattungen")

    def test_manual_rename_during_review_takes_priority(self):
        self.prompt("Build a title renamer")
        self.assertEqual(self.stop()["decision"], "block")
        self.codex.name = "My title"
        self.stop("Thread-Titel: Codex Thread Renamer Skill", active=True)
        self.assertEqual(self.codex.name, "My title")
        self.prompt("A new main goal", turn="second")
        self.assertEqual(self.stop(turn="second"), {})

    def test_no_change_ends_review_and_keeps_title(self):
        self.codex.name = "Codex Thread Renamer Skill"
        self.prompt("thread-title-auto on")
        self.assertEqual(self.stop()["decision"], "block")
        self.assertEqual(self.stop("Titel passt.", active=True), {})
        self.assertEqual(self.stop(), {})
        self.assertEqual(self.codex.name, "Codex Thread Renamer Skill")

    def test_ordinary_reply_and_duplicate_stop_cannot_set_a_title(self):
        self.prompt("Build refunds")
        ordinary_reply = "Thread-Titel: Quoted text from a user"
        self.assertEqual(self.stop(ordinary_reply)["decision"], "block")
        self.assertEqual(self.stop(ordinary_reply, active=True), {})
        self.assertEqual(self.stop("Thread-Titel: A stale result", active=True), {})
        self.assertNotEqual(self.codex.name, "Quoted text from a user")
        self.assertNotEqual(self.codex.name, "A stale result")

    def test_turn_from_other_hook_does_not_start_a_review(self):
        self.prompt("Build refunds")
        self.assertEqual(self.stop("Thread-Titel: A separate hook", active=True), {})
        self.assertNotEqual(self.codex.name, "A separate hook")

    def test_opt_out_persists(self):
        self.prompt("thread-title-auto off")
        self.prompt("Build refunds", turn="second")
        self.assertEqual(self.stop(turn="second"), {})
        self.assertIsNone(self.codex.name)

    def test_malformed_hook_input_is_ignored(self):
        self.assertEqual(self.renamer.handle([], self.data), {})
        self.assertEqual(
            self.renamer.handle(
                {"hook_event_name": "Stop", "session_id": "../other", "turn_id": "turn"},
                self.data,
            ),
            {},
        )

    def test_packaged_hooks_apply_a_proposal_over_jsonl(self):
        stub = self.data / "codex"
        stub.write_text(textwrap.dedent("""\
            #!/usr/bin/env python3
            import json
            import os
            import sys
            from pathlib import Path

            assert sys.argv[1:] == ["app-server", "proxy"]
            storage = Path(os.environ["THREAD_RENAMER_TEST_TITLE"])
            initialized = False
            for line in sys.stdin:
                request = json.loads(line)
                method = request["method"]
                result = {}
                if method == "initialized":
                    initialized = True
                    continue
                if method == "thread/read" and initialized:
                    thread_id = request["params"]["threadId"]
                    current = storage.read_text() if storage.exists() else None
                    result = {"thread": {"id": thread_id, "name": current, "ephemeral": False}}
                elif method == "thread/name/set" and initialized:
                    storage.write_text(request["params"]["name"])
                    print(json.dumps({"method": "thread/name/updated", "params": {}}), flush=True)
                else:
                    assert method == "initialize"
                print(json.dumps({"id": request["id"], "result": result}), flush=True)
            """), encoding="utf-8")
        stub.chmod(0o700)
        plugin_root = RENAMER.parents[1]
        commands = json.loads((plugin_root / "codex-hooks/hooks.json").read_text())["hooks"]
        title_file = self.data / "current-title"
        environment = {
            **os.environ,
            "PATH": str(self.data) + os.pathsep + os.environ["PATH"],
            "PLUGIN_ROOT": str(plugin_root),
            "PLUGIN_DATA": str(self.data / "plugin-data"),
            "THREAD_RENAMER_TEST_TITLE": str(title_file),
        }

        def run(event, **fields):
            payload = {"session_id": THREAD, "turn_id": "first", "hook_event_name": event, **fields}
            command = commands[event][0]["hooks"][0]["command"]
            result = subprocess.run(
                command, shell=True, input=json.dumps(payload), capture_output=True,
                encoding="utf-8", env=environment, check=True, timeout=10,
            )
            return json.loads(result.stdout)

        run("UserPromptSubmit", prompt="Build a thread renamer")
        when_done = run("Stop", last_assistant_message="Implemented.", stop_hook_active=False)
        self.assertEqual(when_done["decision"], "block")
        run("Stop", last_assistant_message="Thread-Titel: Codex Thread Renamer Skill",
            stop_hook_active=True)
        self.assertEqual(title_file.read_text(), "Codex Thread Renamer Skill")


if __name__ == "__main__":
    unittest.main()
