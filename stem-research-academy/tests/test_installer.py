"""The installer's boot-config edit that keeps GPIO18 for ramp servo 2."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

INSTALLER = Path(__file__).resolve().parents[1] / "installer"
SCRIPT = (INSTALLER / "install.sh").read_text(encoding="utf-8")
# Exactly the line MotionModule's installer looks for (installer/install.sh there).
OVERLAY = "dtoverlay=i2c-gpio,i2c_gpio_sda=17,i2c_gpio_scl=18"
PARK = re.search(r"<<'PY' \|\| boot_status=\$\?\n(.*?)\nPY\n", SCRIPT, re.S).group(1)


def park(text):
    with tempfile.TemporaryDirectory() as folder:
        source, result = Path(folder, "config.txt"), Path(folder, "out.txt")
        source.write_text(text, encoding="utf-8")
        status = subprocess.run([sys.executable, "-c", PARK, str(source), str(result), OVERLAY]).returncode
        return status, result.read_text(encoding="utf-8") if result.exists() else None


def active_overlays(text):
    section, found = "[all]", []
    for line in text.splitlines():
        if line.startswith("["):
            section = line.lower()
        elif line == OVERLAY and section != "[none]":
            found.append(section)
    return found


class BootConfigTests(unittest.TestCase):
    def test_the_overlay_matches_motionmodule(self):
        self.assertIn(f"IMU_OVERLAY='{OVERLAY}'", SCRIPT)

    def test_fresh_config_gets_a_parked_copy(self):
        status, text = park("dtparam=audio=on\n[pi4]\narm_boost=1\n")
        self.assertEqual(status, 0)
        self.assertIn(f"[none]\n{OVERLAY}\n[all]\n", text)
        self.assertEqual(active_overlays(text), [])
        self.assertIn(OVERLAY, text.splitlines())  # MotionModule's grep -Fqx finds it

    def test_an_active_copy_from_motionmodule_is_removed(self):
        status, text = park(f"dtparam=audio=on\n\n[all]\n{OVERLAY}\n")
        self.assertEqual(status, 0)
        self.assertEqual(active_overlays(text), [])
        self.assertEqual(text.splitlines().count(OVERLAY), 1)

    def test_running_again_changes_nothing(self):
        _, text = park("dtparam=audio=on\n")
        status, again = park(text)
        self.assertEqual((status, again), (3, None))


@unittest.skipIf(shutil.which("bash") is None, "bash is not available")
class ShellSyntaxTests(unittest.TestCase):
    def test_scripts_parse(self):
        for script in ("install.sh", "curl-install.sh"):
            subprocess.run(["bash", "-n", str(INSTALLER / script)], check=True)


if __name__ == "__main__":
    unittest.main()
