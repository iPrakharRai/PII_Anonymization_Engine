"""
Streamlit Cloud Entrypoint.
Automatically boots the Operator Review Portal from ui/app.py.
"""
import sys
from pathlib import Path
import runpy

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Execute the primary Streamlit application
ui_path = BASE_DIR / "ui" / "app.py"
runpy.run_path(str(ui_path), run_name="__main__")
