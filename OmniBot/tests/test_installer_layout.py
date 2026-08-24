"""Regression checks for the monorepo-aware Raspberry Pi installer."""

from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]
INSTALLER_DIR = PROJECT_DIR / "installer"


class InstallerLayoutTests(unittest.TestCase):
    def test_bootstrap_downloads_installer_from_current_monorepo(self):
        script = (INSTALLER_DIR / "curl-install.sh").read_text(encoding="utf-8")
        self.assertIn(
            "AloeVeraZ/CityTechClubProjects/${REPO_BRANCH}/OmniBot/installer/install.sh",
            script,
        )
        self.assertNotIn("AloeVeraZ/OmniBot", script)

    def test_main_installer_updates_repo_root_and_runs_omnibot_subdirectory(self):
        script = (INSTALLER_DIR / "install.sh").read_text(encoding="utf-8")
        self.assertIn("AloeVeraZ/CityTechClubProjects.git", script)
        self.assertIn('REPO_DIR="${OMNIBOT_REPO_DIR:-$HOME/CityTechClubProjects}"', script)
        self.assertIn('APP_SUBDIR="OmniBot"', script)
        self.assertIn('APP_DIR="$REPO_DIR/$APP_SUBDIR"', script)
        self.assertIn('git -C "$REPO_DIR" fetch', script)
        self.assertIn('"$APP_DIR/omni_robot.py"', script)
        self.assertNotIn('git -C "$APP_DIR"', script)
        self.assertNotIn("AloeVeraZ/OmniBot", script)


if __name__ == "__main__":
    unittest.main()
