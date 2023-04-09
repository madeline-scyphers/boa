import os
import sys
import tempfile
from pathlib import Path

import click

from boa.controller import Controller
from boa.wrappers.script_wrapper import ScriptWrapper
from boa.wrappers.wrapper_utils import cd_and_cd_back, load_jsonlike


@click.command()
@click.option(
    "-c",
    "--config-path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Path to configuration YAML file.",
)
@click.option(
    "-sp",
    "--scheduler-path",
    type=click.Path(),
    default="",
    help="Path to scheduler json file.",
)
@click.option(
    "-wp",
    "--wrapper-path",
    type=click.Path(),
    default="",
    help="Path to where file where your wrapper is located. Used when loaded from scheduler json file,"
    " and the path to your wrapper has changed (such as when loading on a different computer then"
    " originally ran from).",
)
@click.option(
    "-td",
    "--temporary-dir",
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
    "--rel-to-here",
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
def main(config_path, scheduler_path, wrapper_path, temporary_dir, rel_to_here):
    # config_path = config_path if config_path else None
    # scheduler_path = scheduler_path if scheduler_path else None

    if temporary_dir:
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir)
            return run(
                config_path,
                scheduler_path=scheduler_path,
                wrapper_path=wrapper_path,
                rel_to_here=rel_to_here,
                experiment_dir=experiment_dir,
            )
    return run(config_path, scheduler_path=scheduler_path, wrapper_path=wrapper_path, rel_to_here=rel_to_here)


def run(config_path, scheduler_path, rel_to_here, wrapper_path=None, experiment_dir=None):
    """Run experiment run from config path or scheduler path

    Parameters
    ----------
    config_path
        Path to configuration YAML file.
    scheduler_path
        Path to scheduler json file.
    wrapper_path
        Path to where file where your wrapper is located. Used when loaded from scheduler json file,
         and the path to your wrapper has changed (such as when loading on a different computer then
         originally ran from).
    rel_to_here
        Define all path and dir options in your config file relative to where boa is launch from"
        instead of relative to the config file location (the default)"
        ex:
        given working_dir=path/to/dir
        if you don't pass --rel_to_here then path/to/dir is defined in terms of where your config file is
        if you do pass --rel_to_here then path/to/dir is defined in terms of where you launch boa from
    experiment_dir
        experiment output directory to save BOA run to

    Returns
    -------
        Scheduler
    """
    config = {}
    script_options = {}
    ex_options = {}
    if config_path:
        config_path = Path(config_path).resolve()
        config = load_jsonlike(config_path, normalize=False)
        script_options = config.get("script_options", {})
        ex_options = config.get("optimization_options", {})
        rel_to_here = script_options.get("rel_to_config", False) or script_options.get("rel_to_launch", rel_to_here)
    if scheduler_path:
        scheduler_path = Path(scheduler_path).resolve()
    if experiment_dir:
        experiment_dir = Path(experiment_dir).resolve()
    wrapper_path = Path(wrapper_path).resolve() if wrapper_path else None

    if config_path and not rel_to_here:
        rel_path = config_path.parent
    else:
        rel_path = os.getcwd()

    if config:
        options = get_config_options(
            experiment_dir=experiment_dir, rel_path=rel_path, script_options=script_options, ex_options=ex_options
        )
    else:
        options = dict(scheduler_path=scheduler_path, working_dir=Path.cwd())

    sys.path.append(str(rel_path))
    with cd_and_cd_back(options["working_dir"]):
        if scheduler_path:

            controller = Controller.from_scheduler_path(scheduler_path=scheduler_path, wrapper_path=wrapper_path)
        else:
            if options["wrapper_path"] and Path(options["wrapper_path"]).exists():
                options["wrapper"] = options["wrapper_path"]
            else:
                options["wrapper"] = ScriptWrapper
            controller = Controller(
                config_path=config_path,
                **options,
            )
            controller.initialize_scheduler()
        scheduler = controller.run()
        return scheduler


def get_config_options(experiment_dir, rel_path, script_options, ex_options):
    wrapper_name = script_options.get("wrapper_name", "Wrapper")
    append_timestamp = ex_options.get("append_timestamp") or script_options.get("append_timestamp", True)

    wrapper_path = script_options.get("wrapper_path", "wrapper.py")
    wrapper_path = _prepend_rel_path(rel_path, wrapper_path) if wrapper_path else wrapper_path

    working_dir = ex_options.get("working_dir") or script_options.get("working_dir", ".")
    working_dir = _prepend_rel_path(rel_path, working_dir)

    experiment_dir = experiment_dir or ex_options.get("experiment_dir") or script_options.get("experiment_dir")
    experiment_dir = _prepend_rel_path(rel_path, experiment_dir) if experiment_dir else experiment_dir

    if working_dir:
        sys.path.append(str(working_dir))

    return dict(
        append_timestamp=append_timestamp,
        experiment_dir=experiment_dir,
        working_dir=working_dir,
        wrapper_name=wrapper_name,
        wrapper_path=wrapper_path,
    )


def _prepend_rel_path(rel_path, path):
    if not path:
        return path
    path = Path(path)
    if not path.is_absolute():
        path = rel_path / path
    return path.resolve()


if __name__ == "__main__":
    main()
