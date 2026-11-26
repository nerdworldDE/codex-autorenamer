"""Build the skills-only ZIP for OpenAI's public plugin directory."""

import argparse
import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_FILES = (
    "LICENSE",
    "assets/icon.png",
    "skills/codex-thread-renamer/SKILL.md",
    "skills/codex-thread-renamer/LICENSE.txt",
)


def main():
    manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
    del manifest["extensions"]["com.openai"]["hooks"]

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "output",
        nargs="?",
        type=Path,
        default=ROOT / "dist" / f'thread-renamer-{manifest["version"]}.zip',
        help="Destination for the submission ZIP.",
    )
    output = parser.parse_args().output
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("plugin.json", json.dumps(manifest, indent=2) + "\n")
        for name in PACKAGE_FILES:
            archive.writestr(name, (ROOT / name).read_bytes())
    print(output)


if __name__ == "__main__":
    main()
