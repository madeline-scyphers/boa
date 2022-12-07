import os
from pathlib import Path
from typing import TypeVar

ROOT = Path(__file__).resolve().parent.parent

TEST_SCRIPTS_DIR = Path(__file__).resolve().parent / "scripts"
IS_WINDOWS = os.name == "nt"

PathLike = TypeVar("PathLike", str, os.PathLike)
PathLike_tup = (str, os.PathLike)
