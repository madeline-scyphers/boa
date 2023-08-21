import os
import sys
import tempfile
from pathlib import Path

import click
from attrs import fields_dict

from boa.config import BOAScriptOptions
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
    "-wn",
    "--wrapper-name",
    type=str,
    default="",
    help="Name of the wrapper class to use. Used when loaded from scheduler json file,",
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
    "--rel-to-config/--rel-to-here",  # more cli friendly name for config option of rel_to_launch
    default=None,
    help="Define all path and dir options in your config file relative to where boa is launched from"
    " instead of relative to the config file location (the default)"
    " ex:"
    " given working_dir=path/to/dir"
    " if you don't pass --rel-to-here then path/to/dir is defined in terms of where your config file is"
    " if you do pass --rel-to-here then path/to/dir is defined in terms of where you launch boa from",
)
def main(config_path, scheduler_path, wrapper_path, wrapper_name, temporary_dir, rel_to_config):
    """Run experiment run from config path or scheduler path"""

    if temporary_dir:
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir)
            return run(
                config_path,
                scheduler_path=scheduler_path,
                wrapper_path=wrapper_path,
                wrapper_name=wrapper_name,
                rel_to_config=rel_to_config,
                experiment_dir=experiment_dir,
            )
    return run(config_path, scheduler_path=scheduler_path, wrapper_path=wrapper_path, rel_to_config=rel_to_config)


def run(config_path, scheduler_path, rel_to_config, wrapper_path=None, wrapper_name=None, experiment_dir=None):
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
    rel_to_config
        Define all path and dir options in your config file relative to to your config file location
        or rel_to_here (relative to cli launch)
    experiment_dir
        experiment output directory to save BOA run to, can only be specified during an initial run
        (when passing in a config_path, not a scheduler_path)

    Returns
    -------
        Scheduler
    """
    config = {}
    if config_path:
        config_path = Path(config_path).resolve()
        config = load_jsonlike(config_path)
        script_options = config.get("script_options", {})
        if rel_to_config is None:
            rel_to_config = script_options.get("rel_to_config", None) or not script_options.get("rel_to_launch", None)
            if rel_to_config is None:
                rel_to_config = (
                    fields_dict(BOAScriptOptions)["rel_to_config"].default
                    or not fields_dict(BOAScriptOptions)["rel_to_launch"].default
                )
    if scheduler_path:
        scheduler_path = Path(scheduler_path).resolve()
    if experiment_dir:
        experiment_dir = Path(experiment_dir).resolve()
    wrapper_path = Path(wrapper_path).resolve() if wrapper_path else None

    if config_path and rel_to_config:
        rel_path = config_path.parent
    else:
        rel_path = os.getcwd()

    if config:
        options = get_config_options(
            experiment_dir=experiment_dir, rel_path=rel_path, script_options=script_options, wrapper_path=wrapper_path
        )
    else:
        options = dict(scheduler_path=scheduler_path, working_dir=Path.cwd(), wrapper_path=wrapper_path)

    if wrapper_name:
        options["wrapper_name"] = wrapper_name

    with cd_and_cd_back(options["working_dir"]):
        if scheduler_path:
            controller = Controller.from_scheduler_path(**options)
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


def get_config_options(experiment_dir, rel_path, script_options, wrapper_path=None):
    wrapper_name = script_options.get("wrapper_name", fields_dict(BOAScriptOptions)["wrapper_name"].default)
    append_timestamp = (
        script_options.get("append_timestamp", None)
        if script_options.get("append_timestamp", None) is not None
        else fields_dict(BOAScriptOptions)["append_timestamp"].default
    )

    wrapper_path = (
        wrapper_path
        if wrapper_path is not None
        else script_options.get("wrapper_path", fields_dict(BOAScriptOptions)["wrapper_path"].default)
    )
    wrapper_path = _prepend_rel_path(rel_path, wrapper_path) if wrapper_path else wrapper_path

    working_dir = script_options.get("working_dir", fields_dict(BOAScriptOptions)["working_dir"].default)
    working_dir = _prepend_rel_path(rel_path, working_dir)

    experiment_dir = experiment_dir or script_options.get(
        "experiment_dir", fields_dict(BOAScriptOptions)["experiment_dir"].default
    )
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
