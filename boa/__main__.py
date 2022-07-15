import importlib.util
from pathlib import Path
import sys

import click

from boa.controller import Controller


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
    is_flag=True, show_default=True, default=True, help="append timestamp to experiment directory"
)
def main(config_path, wrapper_path, wrapper_name, append_timestamp):
    module_name = "user_wrapper"
    spec = importlib.util.spec_from_file_location(module_name, wrapper_path)

    user_wrapper = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = user_wrapper
    spec.loader.exec_module(user_wrapper)

    wrapper_cls = getattr(user_wrapper, wrapper_name)
    print(user_wrapper)
    print(wrapper_cls)

    controller = Controller(config_path=config_path, wrapper=wrapper_cls)
    controller.run(append_timestamp=append_timestamp)


if __name__ == "__main__":
    main()
