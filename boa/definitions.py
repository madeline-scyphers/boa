from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TEST_SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
IS_WINDOWS = os.name == "nt"

PathLike = str | os.PathLike
