import importlib.util
import sys
from pathlib import Path

import click

from boa.controller import Controller
from boa.wrapper_utils import cd_and_cd_back


@click.command()
@click.option(
    "-c",
    "--config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration YAML file.",
)
@click.option(
    "-w",
    "--wrapper_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path(__file__).resolve().parent / "opt_config.yaml",
    help="Path to file with boa wrapper class",
)
@click.option(
    "-wn",
    "--wrapper_name",
    type=str,
    default="Wrapper",
    help="Name of wrapper class in boa wrapper class file",
)
@click.option(
    "-at",
    "--append_timestamp",
    is_flag=True,
    show_default=True,
    default=True,
    help="Whether to append a timestamp to the end of the experiment directory to ensure uniqueness",
)
@click.option(
    "-d",
    "--working_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Path to working dir to to cd to. "
    "Can be necessary for certain languages and projects that need to be in a certain directory for imports.",
)
def main(config_path, wrapper_path, wrapper_name, append_timestamp, working_dir):
    if working_dir:
        sys.path.append(str(working_dir))
    with cd_and_cd_back(working_dir):
        module_name = "user_wrapper"
        spec = importlib.util.spec_from_file_location(module_name, wrapper_path)

        user_wrapper = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = user_wrapper
        spec.loader.exec_module(user_wrapper)

        wrapper_cls = getattr(user_wrapper, wrapper_name)

        controller = Controller(config_path=config_path, wrapper=wrapper_cls)
        controller.run(append_timestamp=append_timestamp)


if __name__ == "__main__":
    main()
