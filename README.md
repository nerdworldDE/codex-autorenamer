# Codex Thread Renamer

Give the current conversation a title you can find later. When a question about whether Codex can rename threads turns into a request to build a skill, **Codex Thread Renamer Skill** describes the new goal.

[Deutsch](README.de.md)

## Rename on request

Install the Agent Skill in Codex, Cursor, Claude Code, or another supported agent.

```sh
npx skills add nerdworldDE/codex-autorenamer --skill codex-thread-renamer
```

Select `codex-thread-renamer` in your client and ask it to rename the conversation. The skill applies the title when the client exposes a conversation-title tool. In other clients it returns a title you can use. [Agent Skill](skills/codex-thread-renamer/SKILL.md)

## Enable automatic titles in Codex

The local plugin uses Python 3.9 or newer on Linux or macOS and needs the local Codex App Server on its default Unix socket. Install from a checkout of this repository.

```sh
git clone https://github.com/nerdworldDE/codex-autorenamer.git
cd codex-autorenamer
codex plugin marketplace add .
codex plugin add codex-thread-renamer@local-thread-renamer
```

Restart Codex and review the two hooks in `/hooks`. If your CLI uses an embedded server, start the daemon with `codex app-server daemon start` and connect with `codex --remote unix://`. [Codex hooks](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks) · [App Server](https://learn.chatgpt.com/docs/app-server#connect-the-cli-terminal-ui)

- **New threads.** When the plugin sees an unnamed thread, it gives it an initial title. At the end of a turn, Codex makes a short additional model pass to check whether the current title still fits. Your client may display the proposal as a short follow-up.
- **Existing threads.** Send `thread-title-auto on` to let the plugin manage the current title. Send `thread-title-auto off` to pause automation for that thread.
- **Manual titles.** A title change detected by the plugin pauses automation. The plugin reads the current title immediately before writing. The App Server uses separate read and write calls, so simultaneous edits can overlap.

## Development

```sh
python3 -B -m unittest discover -s tests -v
```

The tests simulate Codex hook events and App Server responses. They cover title updates, intervening manual edits, the installed hook entry point, and the OpenAI submission ZIP. [Release and directory submission](docs/releasing.md)

[MIT license](LICENSE)
