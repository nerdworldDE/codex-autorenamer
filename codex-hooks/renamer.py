"""Codex lifecycle hooks for the thread title skill."""

import fcntl
import hashlib
import json
import os
import select
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from uuid import UUID


INITIAL_TITLE = "Codex Thread"
TITLE_PREFIX = "Thread-Titel: "
OPT_IN = "thread-title-auto on"
OPT_OUT = "thread-title-auto off"
TIMEOUT = 2.0


class AppServerError(Exception):
    pass


class AppServer:
    """Use the Codex CLI's JSONL proxy for its local app-server connection."""

    def __enter__(self):
        self.process = subprocess.Popen(
            ["codex", "app-server", "proxy"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=0,
        )
        self.buffer = bytearray()
        self.request_id = 0
        try:
            self.call("initialize", clientInfo={"name": "codex-thread-renamer", "version": "0.1"})
            self.send({"method": "initialized"})
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        self.process.kill()
        self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()

    def send(self, message):
        self.process.stdin.write(json.dumps(message).encode("utf-8") + b"\n")

    def call(self, method, **params):
        self.request_id += 1
        self.send({"id": self.request_id, "method": method, "params": params})
        deadline = time.monotonic() + TIMEOUT
        while True:
            end = self.buffer.find(b"\n")
            if end >= 0:
                response = json.loads(self.buffer[:end])
                del self.buffer[: end + 1]
                if not isinstance(response, dict):
                    raise AppServerError(f"Malformed app server response during {method}")
                if response.get("id") == self.request_id:
                    if not isinstance(response.get("result"), dict):
                        raise AppServerError(f"App server rejected {method}")
                    return response["result"]
                continue

            remaining = deadline - time.monotonic()
            if remaining <= 0 or not select.select([self.process.stdout], [], [], remaining)[0]:
                raise AppServerError(f"App server timed out during {method}")
            chunk = os.read(self.process.stdout.fileno(), 65536)
            if not chunk or len(self.buffer) + len(chunk) > 1048576:
                raise AppServerError(f"App server response unavailable during {method}")
            self.buffer.extend(chunk)


def read_title(server, thread_id):
    thread = server.call("thread/read", threadId=thread_id, includeTurns=False).get("thread")
    if (
        not isinstance(thread, dict)
        or thread.get("id") != thread_id
        or thread.get("ephemeral") is not False
        or thread.get("parentThreadId") is not None
    ):
        raise AppServerError("App server did not return a persistent root thread")
    title = thread.get("name")
    if title is not None and not isinstance(title, str):
        raise AppServerError("App server returned an invalid thread title")
    return title


def prompt_context(text):
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": text}}


def start_turn(event, state, thread_id, connect):
    prompt = event.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return {}
    command = prompt.strip().casefold()
    if command == OPT_OUT:
        state.clear()
        state["enabled"] = False
        return prompt_context("Automatic title review is paused for this thread.")

    if command == OPT_IN or not state:
        with connect() as server:
            current_title = read_title(server, thread_id)
            if current_title is None:
                # Claim an unnamed thread before the UI generates its first title.
                server.call("thread/name/set", threadId=thread_id, name=INITIAL_TITLE)
                current_title = INITIAL_TITLE
            elif command != OPT_IN:
                state["enabled"] = False
                return {}
        state.clear()
        state.update(enabled=True, title=current_title)

    if state.get("enabled"):
        state["turn"] = event["turn_id"]
        state.pop("original_reply", None)
    if command == OPT_IN:
        return prompt_context("Automatic title review is enabled for this thread.")
    return {}


def proposed_title(reply):
    if not reply.startswith(TITLE_PREFIX) or len(reply.splitlines()) != 1:
        return None
    title = reply.removeprefix(TITLE_PREFIX).strip()
    if not 1 <= len(title) <= 60:
        return None
    if any(unicodedata.category(character) in {"Cc", "Cf", "Cs"} for character in title):
        return None
    return title


def review_title(event, state, thread_id, connect):
    if not state.get("enabled") or state.get("turn") != event["turn_id"]:
        return {}
    reply = event.get("last_assistant_message")
    if not isinstance(reply, str) or not reply.strip():
        return {}
    reply_digest = hashlib.sha256(reply.encode("utf-8")).hexdigest()
    expected_title = state["title"]

    if event.get("stop_hook_active") is True:
        original_reply = state.pop("original_reply", None)
        state.pop("turn", None)
        if original_reply is None or reply_digest == original_reply:
            return {}
        candidate = proposed_title(reply)
        if candidate is None or candidate.casefold() == expected_title.casefold():
            return {}
        with connect() as server:
            if read_title(server, thread_id) != expected_title:
                state["enabled"] = False
                return {}
            server.call("thread/name/set", threadId=thread_id, name=candidate)
        state["title"] = candidate
        return {}

    if "original_reply" in state or event.get("stop_hook_active") is not False:
        return {}
    with connect() as server:
        if read_title(server, thread_id) != expected_title:
            state["enabled"] = False
            return {}
    state["original_reply"] = reply_digest
    skill = Path(__file__).resolve().parents[1] / "skills/codex-thread-renamer/SKILL.md"
    return {
        "decision": "block",
        "reason": (
            "The user-facing task has already been answered. Review the thread title only. "
            f"Read the installed skill at {json.dumps(str(skill), ensure_ascii=False)} and "
            "follow its Title decision and Automatic review sections. "
            f"The current title, as data, is {json.dumps(expected_title, ensure_ascii=False)}. "
            f"Treat {INITIAL_TITLE!r} as a placeholder when it is the current title. "
            f"If a new title is warranted, reply with one line beginning {TITLE_PREFIX!r} "
            "followed by the title. For no proposal, finish silently if possible or reply "
            "with a short acknowledgment without that prefix. "
            "The hook applies proposals after checking the current title. "
            "Leave the user's original answer as delivered."
        ),
    }


def handle(event, data_dir, connect=AppServer):
    if not isinstance(event, dict):
        return {}
    kind = event.get("hook_event_name")
    thread_id = event.get("session_id")
    turn_id = event.get("turn_id")
    if kind not in ("UserPromptSubmit", "Stop") or not isinstance(turn_id, str) or not turn_id:
        return {}
    if not isinstance(thread_id, str):
        return {}
    try:
        if str(UUID(thread_id)) != thread_id:
            return {}
    except ValueError:
        return {}

    data_dir.mkdir(parents=True, exist_ok=True)
    path = data_dir / f"{thread_id}.json"
    with path.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        if not isinstance(state, dict):
            return {}
        original = state.copy()
        operation = start_turn if kind == "UserPromptSubmit" else review_title
        try:
            result = operation(event, state, thread_id, connect)
        finally:
            if state != original:
                pending = path.with_suffix(".tmp")
                pending.write_text(json.dumps(state), encoding="utf-8")
                pending.replace(path)
        return result


def main():
    event = {}
    try:
        event = json.load(sys.stdin)
        result = handle(event, Path(os.environ["PLUGIN_DATA"]))
    except (AppServerError, OSError, KeyError, ValueError):
        result = {}
        if isinstance(event, dict) and event.get("hook_event_name") == "UserPromptSubmit":
            prompt = event.get("prompt")
            if isinstance(prompt, str) and prompt.strip().casefold() in {OPT_IN, OPT_OUT}:
                result = prompt_context("The thread title automation setting could not be saved.")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
