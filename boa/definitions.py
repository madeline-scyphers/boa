import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEST_SCRIPTS_DIR = Path(__file__).resolve().parent / "test_scripts"
IS_WINDOWS = os.name == "nt"
