from pathlib import Path
from unittest.mock import patch
import importlib
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class WebUiEntrypointTest(unittest.TestCase):
    def test_streamlit_is_the_only_webui_entrypoint(self):
        self.assertTrue((PROJECT_ROOT / "main_streamlit.py").exists())
        self.assertFalse((PROJECT_ROOT / "main_ui.py").exists())
        self.assertFalse((PROJECT_ROOT / "audiobook_generator/ui/web_ui.py").exists())

    def test_requirements_do_not_include_gradio(self):
        requirements = (PROJECT_ROOT / "requirements.txt").read_text()
        self.assertNotIn("gradio", requirements)
        self.assertIn("streamlit", requirements)

    def test_streamlit_entrypoint_does_not_run_on_import(self):
        sys.modules.pop("main_streamlit", None)

        with patch("audiobook_generator.ui.streamlit_ui.run_app") as run_app:
            importlib.import_module("main_streamlit")

        run_app.assert_not_called()


if __name__ == "__main__":
    unittest.main()
