import sys
import tempfile
from pathlib import Path
from typing import Optional

import click

from boa.config import BOAConfig
from boa.controller import Controller
from boa.wrappers.script_wrapper import ScriptWrapper
from boa.wrappers.wrapper_utils import cd_and_cd_back


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
        experiment output directory to save BOA run to, can only be specified during an initial run
        (when passing in a config_path, not a scheduler_path)

    Returns
    -------
        Scheduler
    """
    config: Optional[BOAConfig] = None
    if config_path:
        config_path = Path(config_path).resolve()
        config = BOAConfig.from_jsonlike(file=config_path, rel_to_config=not rel_to_here)
    if scheduler_path:
        scheduler_path = Path(scheduler_path).resolve()
    if experiment_dir:
        experiment_dir = Path(experiment_dir).resolve()
        if config:
            config.script_options.experiment_dir = experiment_dir
    wrapper_path = Path(wrapper_path).resolve() if wrapper_path else None

    if config:
        options = dict(
            append_timestamp=config.script_options.append_timestamp,
            experiment_dir=config.script_options.experiment_dir,
            working_dir=config.script_options.working_dir,
            wrapper_name=config.script_options.wrapper_name,
            wrapper_path=config.script_options.wrapper_path,
        )
    else:
        options = dict(scheduler_path=scheduler_path, working_dir=Path.cwd())

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
        if not config:
            config = controller.config
        if config and config.script_options:
            sys.path.append(str(config.script_options.working_dir))
            sys.path.append(str(config.script_options.base_path))

        scheduler = controller.run()
        return scheduler


if __name__ == "__main__":
    main()
