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
        self.assertIn("Acquire::Retries=3", script)
        self.assertIn("dpkg --configure -a", script)
        self.assertIn("timedatectl set-ntp true", script)
        self.assertIn("update-ca-certificates", script)
        self.assertIn("apt_log_has_certificate_error", script)
        self.assertIn("TLS verification was not disabled", script)
        self.assertIn("install_package ca-certificates", script)
        self.assertIn("command sudo -n true", script)
        self.assertIn('sudo() { command sudo -n "$@"; }', script)
        self.assertNotIn("sudo -v", script)
        self.assertIn("install_package python3-opencv", script)
        self.assertIn("install_package v4l-utils", script)
        self.assertIn('"$APP_DIR/camera_stream.py"', script)
        self.assertIn('install_one_of "Raspberry Pi GPIO"', script)
        self.assertIn('install_one_of "Nginx"', script)
        self.assertIn("===== Last apt output =====", script)
        self.assertNotIn('git -C "$APP_DIR"', script)
        self.assertNotIn("AloeVeraZ/OmniBot", script)

    def test_reruns_skip_unchanged_installation_work(self):
        script = (INSTALLER_DIR / "install.sh").read_text(encoding="utf-8")
        self.assertIn("all_packages_ready", script)
        self.assertIn("skipping apt", script)
        self.assertIn("diff --quiet", script)
        self.assertIn(
            '"$REPO_COMMIT_BEFORE" "$REPO_COMMIT_AFTER" -- "$APP_SUBDIR"',
            script,
        )
        self.assertIn("install_root_file_if_changed", script)
        self.assertIn("install_user_file_if_changed", script)
        self.assertIn("sudo cmp -s", script)
        self.assertIn("Nginx configuration is unchanged", script)
        self.assertIn("Code and dependencies are unchanged", script)
        self.assertIn("Rolling the repository back", script)
        self.assertIn("Restoring the previous repository", script)
        self.assertIn("systemd-run", script)


if __name__ == "__main__":
    unittest.main()
