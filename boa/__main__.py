import importlib.util
import sys
import tempfile
import time
from pathlib import Path

import click

from boa.controller import Controller
from boa.wrappers.wrapper_utils import cd_and_cd_back, load_jsonlike


@click.command()
@click.option(
    "-c",
    "--config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
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
    " to ``load_config``. The default ``load_config`` does support this.",
)
@click.option(
    "-rel",
    "--rel_to_here",
    is_flag=True,
    show_default=True,
    default=False,
    help="Define all path and dir options in your config file relative to where boa is launch from"
    " instead of relative to the config file location (the default)"
    " ex:"
    " given working_dir=path/to/dir"
    " if you don't pass --rel_to_here then path/to/dir is defined in terms of where your config file is"
    " if you do pass --rel_to_here then path/to/dir is defined in terms of where you launch boa from",
)
def main(config_path, temporary_dir, rel_to_here):
    if temporary_dir:
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir) / "temp"
            return _main(config_path, rel_to_here, experiment_dir)
    return _main(config_path, rel_to_here=rel_to_here)


def _main(config_path, rel_to_here, experiment_dir=None):
    s = time.time()
    config_path = Path(config_path).resolve()
    rel_path = config_path.parent
    if rel_to_here:
        rel_path = Path.cwd()

    config = load_jsonlike(config_path, normalize=False)

    script_options = config.get("script_options", {})
    wrapper_name = script_options.get("wrapper_name", "Wrapper")
    append_timestamp = script_options.get("append_timestamp", True)

    wrapper_path = script_options.get("wrapper_path", "wrapper.py")
    wrapper_path = _prepend_rel_path(rel_path, wrapper_path) if wrapper_path else wrapper_path

    working_dir = script_options.get("working_dir", ".")
    working_dir = _prepend_rel_path(rel_path, working_dir)

    experiment_dir = experiment_dir or script_options.get("experiment_dir")
    experiment_dir = _prepend_rel_path(rel_path, experiment_dir) if experiment_dir else experiment_dir

    if working_dir:
        sys.path.append(str(working_dir))
    sys.path.append(str(rel_path))
    with cd_and_cd_back(working_dir):
        if wrapper_path.exists():
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
            from boa.wrappers.script_wrapper import ScriptWrapper as WrapperCls

        controller = Controller(config_path=config_path, wrapper=WrapperCls)
        controller.setup(append_timestamp=append_timestamp, experiment_dir=experiment_dir)
        scheduler = controller.run()
        print(f"total time = {time.time() - s}")
        return scheduler


def _prepend_rel_path(rel_path, path):
    path = Path(path)
    if not path.is_absolute():
        path = rel_path / path
    return path.resolve()


if __name__ == "__main__":
    main()
