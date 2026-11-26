import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
SKILL = "skills/codex-thread-renamer/SKILL.md"


class ReleasePackageTests(unittest.TestCase):
    def test_openai_archive_contains_the_portable_skill_and_listing_assets(self):
        builder = ROOT / "scripts/build_openai_package.py"
        self.assertTrue(builder.is_file(), "Missing public-directory package builder")
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "portable skill.zip"
            subprocess.run([sys.executable, str(builder), str(target)], capture_output=True, check=True)
            with ZipFile(target) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {"plugin.json", "LICENSE", "assets/icon.png", SKILL,
                     "skills/codex-thread-renamer/LICENSE.txt"},
                )
                manifest = json.loads(archive.read("plugin.json"))
                openai = manifest["extensions"]["com.openai"]
                self.assertNotIn("hooks", openai)
                self.assertEqual(archive.read(SKILL), (ROOT / SKILL).read_bytes())
                self.assertEqual(
                    archive.read("skills/codex-thread-renamer/LICENSE.txt"),
                    archive.read("LICENSE"),
                )
                for key in ("logo", "composerIcon"):
                    image = archive.read(openai["interface"][key].removeprefix("./"))
                    self.assertEqual(image[:8], b"\x89PNG\r\n\x1a\n")
                self.assertIsNone(archive.testzip())


if __name__ == "__main__":
    unittest.main()
