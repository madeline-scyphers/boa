import inspect
from pathlib import Path

FILENAME = Path(__file__).name


def get_calling_file_path():
    frames = inspect.stack()
    frame = 1
    while (file_path := Path(frames[frame].filename)).name == FILENAME:
        frame += 1
    return file_path


def add_ref_to_rel_init():
    file_path = get_calling_file_path()

    parent = file_path.parent
    pathing_ls = []
    for part in reversed(parent.parts):
        pathing_ls.append(part)
        if part == "boa":
            break
    pathing = ".".join(module for module in reversed(pathing_ls))

    return f"""**See More Information Here**: :mod:`{pathing}`"""
