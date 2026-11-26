# Codex Thread Renamer

Der Skill gibt dem aktuellen Thread einen auffindbaren Titel, sobald aus einer offenen Frage ein konkreter Auftrag wird oder sich das Hauptziel ändert. Wenn aus „Kann Codex seinen Thread selbst umbenennen?“ ein Entwicklungsauftrag wird, lautet der Titel zum Beispiel **Codex Thread Renamer Skill**.

## Umbenennung auf Zuruf

```sh
npx skills add nerdworldDE/codex-autorenamer --skill codex-thread-renamer
```

Wähle `codex-thread-renamer` im KI-Client und bitte um einen treffenderen Titel. Hat der Client ein Werkzeug zum Umbenennen, setzt der Skill den Titel direkt. In anderen Clients liefert er einen Vorschlag. [SKILL.md](skills/codex-thread-renamer/SKILL.md)

## Automatik in Codex aktivieren

Das Plugin benötigt Python 3.9 oder neuer unter Linux oder macOS und die lokale Codex CLI mit App Server am Standard-Unix-Socket.

```sh
git clone https://github.com/nerdworldDE/codex-autorenamer.git
cd codex-autorenamer
codex plugin marketplace add .
codex plugin add codex-thread-renamer@local-thread-renamer
```

Starte Codex neu, öffne `/hooks` und prüfe und bestätige die beiden Hooks. Falls deine CLI-Sitzung einen eingebetteten Server verwendet, starte den lokalen Daemon mit `codex app-server daemon start` und öffne Codex über `codex --remote unix://`. [Codex-Hooks](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks) · [Lokaler App Server](https://learn.chatgpt.com/docs/app-server#connect-the-cli-terminal-ui)

- **Neue Threads.** Erkennt das Plugin einen unbenannten Thread, vergibt es einen vorläufigen Titel. Am Ende des Turns prüft Codex den Titel in einem kurzen zusätzlichen Modellschritt. Je nach Client kann der Vorschlag als Folgemeldung erscheinen.
- **Bestehende Threads.** Sende `thread-title-auto on`, um den vorhandenen Titel für die Automatik freizugeben. Mit `thread-title-auto off` pausierst du sie für den aktuellen Thread.
- **Manueller Vorrang.** Erkennt das Plugin eine manuelle Umbenennung, pausiert es die Automatik. Es liest den Titel unmittelbar vor dem Schreiben erneut. Bei exakt gleichzeitigen Änderungen können sich die Schreibvorgänge überschneiden.

[Tests und Veröffentlichung](README.md#development) · [MIT-Lizenz](LICENSE)
