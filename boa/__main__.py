import importlib.util
import sys
import tempfile
from pathlib import Path

import click

from boa.controller import Controller
from boa.wrapper_utils import cd_and_cd_back, load_jsonlike


@click.command()
@click.option(
    "-c",
    "--config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Path to configuration YAML file.",
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
# --rel_to_here
def main(config_path, temporary_dir, rel_to_here=False):
    if temporary_dir:
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "temp"
            return _main(config_path, rel_to_here, experiment_dir)
    return _main(config_path, rel_to_here=rel_to_here)


def _main(config_path, rel_to_here, experiment_dir=None):
    config = load_jsonlike(config_path, normalize=False)

    script_options = config.get("script_options", {})
    wrapper_path = script_options.get("wrapper_path")
    wrapper_name = script_options.get("wrapper_name", "Wrapper")
    working_dir = script_options.get("working_dir")
    experiment_dir = experiment_dir or script_options.get("experiment_dir")
    append_timestamp = script_options.get("append_timestamp", True)

    config_path = Path(config_path).resolve()
    wrapper_path = Path(wrapper_path).resolve() if wrapper_path else wrapper_path
    working_dir = Path(working_dir).resolve() if working_dir else working_dir

    if working_dir:
        sys.path.append(str(working_dir))
    with cd_and_cd_back(working_dir):
        if wrapper_path:
            # create a module spec from a file location so we can then load that module
            module_name = "user_wrapper"
            spec = importlib.util.spec_from_file_location(module_name, wrapper_path)
            # create that module from that spec from above
            user_wrapper = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = user_wrapper
            # execute the loading and importing of the module
            spec.loader.exec_module(user_wrapper)

            # since we just loaded the module where the wrapper class is, we can now load it
            WrapperCls = getattr(user_wrapper, wrapper_name)
        else:
            from boa.wrapper import BaseWrapper as WrapperCls

        controller = Controller(config_path=config_path, wrapper=WrapperCls)
        scheduler = controller.run(append_timestamp=append_timestamp, experiment_dir=experiment_dir)
        return scheduler


if __name__ == "__main__":
    main()
