import importlib.util
import sys
import tempfile
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
    "-d",
    "--working_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Path to working dir to to cd to. "
    "Can be necessary for certain languages and projects that need to be in a certain directory for imports.",
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
    "-o",
    "--experiment_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Modify/add to the config file the passed in experiment_dir for use downstream."
    " This requires your Wrapper to have the ability to take experiment_dir as an argument"
    " to ``load_config``. The default ``load_config`` does support this."
    " --experiment_dir and --temp_dir can't both be used.",
)
@click.option(
    "-td",
    "--temporary_dir",
    is_flag=True,
    show_default=True,
    default=False,
    help="Modify/add to the config file a temporary directory as the experiment_dir that will get deleted after running"
    " (useful for testing)."
    " This requires your Wrapper to have the ability to take experiment_dir as an argument"
    " to ``load_config``. The default ``load_config`` does support this."
    " --experiment_dir and --temp_dir can't both be used.",
)
def main(config_path, wrapper_path, wrapper_name, working_dir, append_timestamp, experiment_dir, temporary_dir):
    if temporary_dir:
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "temp"
            return _main(config_path, wrapper_path, wrapper_name, working_dir, append_timestamp, experiment_dir)
    return _main(config_path, wrapper_path, wrapper_name, working_dir, append_timestamp, experiment_dir)


def _main(config_path, wrapper_path, wrapper_name, working_dir, append_timestamp, experiment_dir):
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
        scheduler = controller.run(append_timestamp=append_timestamp, experiment_dir=experiment_dir)
        return scheduler


if __name__ == "__main__":
    main()
