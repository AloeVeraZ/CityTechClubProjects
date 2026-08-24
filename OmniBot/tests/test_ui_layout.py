"""Static regression checks for the Raspberry Pi display layout."""

from pathlib import Path
import unittest


PROJECT_DIR = Path(__file__).resolve().parents[1]


class LocalDisplayLayoutTests(unittest.TestCase):
    def test_local_ui_reserves_the_desktop_top_panel(self):
        source = (PROJECT_DIR / "omni_robot.py").read_text(encoding="utf-8")
        self.assertIn('OMNIBOT_TOP_PANEL_HEIGHT", "40"', source)
        self.assertIn("DISPLAY_HEIGHT - TOP_PANEL_HEIGHT", source)
        self.assertIn('SDL_VIDEO_WINDOW_POS", f"0,{TOP_PANEL_HEIGHT}"', source)
        self.assertIn("pygame.NOFRAME", source)


if __name__ == "__main__":
    unittest.main()
