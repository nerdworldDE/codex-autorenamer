# Release and directory submission

## GitHub and skills.sh

Publish this repository under `nerdworldDE/codex-autorenamer`. From a separate, temporary project, verify installation using the public repository URL.

```sh
npx skills add nerdworldDE/codex-autorenamer --skill codex-thread-renamer
```

skills.sh discovers public skills through installation telemetry. It lists use across agents including Codex, Cursor, and Claude Code. [skills.sh FAQ](https://www.skills.sh/docs/faq#how-do-i-get-my-skill-listed-on-the-leaderboard)

## OpenAI Plugin Directory

Build the **Thread Renamer** submission ZIP.

```sh
python3 scripts/build_openai_package.py
```

The ZIP contains the standalone skill, listing metadata, icon, and license. OpenAI accepts skills-only submissions for the public directory shared by ChatGPT and Codex. The GitHub release provides the local Codex automation with lifecycle hooks, which OpenAI excludes from public plugin submissions. [OpenAI package rules](https://developers.openai.com/plugins/build/plugins#bundled-mcp-servers-and-lifecycle-hooks)

1. Select a verified developer identity in the [OpenAI Plugins dashboard](https://platform.openai.com/plugins).
2. Upload `dist/thread-renamer-0.1.0.zip` as a skills-only plugin and resolve the validation findings.
3. Test the skill in a conversation that shifts from a question to a concrete project. Ask for a searchable title and check that it names the concrete goal. In a client without a rename tool, the skill should return a suggestion.
4. Submit for review and publish after approval. [OpenAI submission guide](https://developers.openai.com/plugins/deploy/submission)

## Cursor Marketplace

After the GitHub source is public, use the repository's root `plugin.json` as the Agent Plugins manifest. Submit the repository URL through Cursor's review form. Cursor users can also install the standalone skill with the skills CLI. [Cursor Marketplace submission](https://cursor.com/marketplace/publish) · [Plugin requirements](https://cursor.com/docs/reference/plugins)

## Awesome Agent Skills

The maintainers ask for demonstrated community use before listing a skill. Once the project meets that requirement, submit a link to its public skill directory under Productivity and Collaboration. [Contribution guidelines](https://github.com/VoltAgent/awesome-agent-skills/blob/main/CONTRIBUTING.md)
