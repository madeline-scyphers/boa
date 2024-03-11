# weird file name with dash in it because CLI conventions
import dataclasses
import os
import sys
import tempfile
from pathlib import Path

import click
import pandas as pd
from attrs import fields_dict
from ax import Data
from ax.storage.json_store.decoder import object_from_json

from boa.config import BOAConfig, BOAScriptOptions, MetricType
from boa.controller import Controller
from boa.storage import scheduler_from_json_file
from boa.utils import check_min_package_version
from boa.wrappers.synthetic_wrapper import SyntheticWrapper
from boa.wrappers.wrapper_utils import load_jsonlike


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
    "-n",
    "--num-trials",
    type=int,
    help="Number of trials to run. Overrides trials in config file.",
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
    " to ``load_config``. The default ``load_config`` does support this."
    " This is also only done for initial run, not for reloading from scheduler json file.",
)
def main(config_path, scheduler_path, num_trials, temporary_dir):
    """Asynchronous optimization script. Asynchronously run your optimization.
    With this script, you can pass in a configuration file that specifies your
    optimization parameters and objective and BOA will output a
    optimization.csv file with your parameters.

    BLAH BLAH BLAH

    Parameters
    ----------
    config_path
        Path to configuration YAML file.
    scheduler_path
        Path to scheduler json file.
    num_trials
        Number of trials to run. Overrides trials in config file.

    Returns
    -------
        Scheduler
    """
    if temporary_dir:
        with tempfile.TemporaryDirectory() as temp_dir:
            experiment_dir = Path(temp_dir)
            return run(
                config_path=config_path,
                scheduler_path=scheduler_path,
                num_trials=num_trials,
                experiment_dir=experiment_dir,
            )
    return run(
        config_path=config_path,
        scheduler_path=scheduler_path,
        num_trials=num_trials,
    )


def run(config_path, scheduler_path, num_trials, experiment_dir=None):
    if experiment_dir:
        experiment_dir = Path(experiment_dir).resolve()
    # set num_trials before loading config because scheduler options is frozen
    config_kw = (
        dict(
            n_trials=num_trials,
            scheduler=dict(total_trials=None, n_trials=None),
        )
        if num_trials
        else {}
    )

    config = None
    if config_path:
        config = BOAConfig.from_jsonlike(config_path, **config_kw)
    if scheduler_path:
        scheduler_path = Path(scheduler_path).resolve()
        if not config:
            sch_jsn = load_jsonlike(scheduler_path)
            config = BOAConfig(**{**object_from_json(sch_jsn["wrapper"]["config"]), **config_kw})
    if "steps" in config.generation_strategy:
        for step in config.generation_strategy["steps"]:
            step.max_parallelism = None
    else:
        config.generation_strategy["max_parallelism_override"] = -1
    for metric in config.objective.metrics:
        metric.metric = "passthrough"
        metric.metric_type = MetricType.PASSTHROUGH
    if experiment_dir:
        config.script_options.experiment_dir = experiment_dir

    if scheduler_path:
        scheduler = scheduler_from_json_file(filepath=scheduler_path)
        if num_trials:
            scheduler.wrapper.config.scheduler = dataclasses.replace(
                scheduler.wrapper.config.scheduler, total_trials=num_trials
            )
            scheduler.wrapper.config.n_trials = num_trials
            scheduler.options = dataclasses.replace(scheduler.options, total_trials=num_trials)
    else:
        controller = Controller(config_path=config_path, wrapper=SyntheticWrapper(config=config))
        controller.initialize_scheduler()
        scheduler = controller.scheduler

    if not scheduler.opt_csv.exists() and scheduler.experiment.trials:
        controller.logger.warning(
            "No optimization CSV found, but previous trials exist. "
            "\nLikely cause was a previous run was moved with out the CSV."
        )

    if scheduler.opt_csv.exists():
        exp_attach_data_from_opt_csv(list(config.objective.metric_names), scheduler)

    generator_runs = scheduler.generation_strategy._gen_multiple(
        experiment=scheduler.experiment, num_generator_runs=scheduler.wrapper.config.trials
    )

    for generator_run in generator_runs:
        trial = scheduler.experiment.new_trial(
            generator_run=generator_run,
        )
        trial.runner = scheduler.runner
        trial.mark_running()

    if scheduler.experiment.fetch_data().df.empty:
        trials = scheduler.experiment.trials
        metrics = scheduler.experiment.metrics
        scheduler.experiment.attach_data(
            Data(
                df=pd.DataFrame(
                    dict(
                        trial_index=[i for i in trials.keys() for m in metrics.keys()],
                        arm_name=[f"{i}_0" for i in trials.keys() for m in metrics.keys()],
                        metric_name=[m for i in trials.keys() for m in metrics.keys()],
                        mean=None,
                        sem=0.0,
                    )
                )
            )
        )

    scheduler.save_data(metrics_to_end=True, ax_kwargs=dict(always_include_field_columns=True))
    return scheduler


def exp_attach_data_from_opt_csv(metric_names, scheduler):
    df = pd.read_csv(scheduler.opt_csv)
    isin = df.columns.isin(metric_names).sum() == len(metric_names)
    if not isin:
        return

    exp_df = scheduler.experiment.fetch_data().df
    nan_rows = exp_df["mean"].isna()
    nan_trials = exp_df.loc[nan_rows]["trial_index"].unique()
    new_data = df.loc[df["trial_index"].isin(nan_trials)]
    if new_data.empty:
        return
    metric_data = new_data[metric_names].to_dict()
    if check_min_package_version("ax-platform", "0.3.3"):
        kw = dict(combine_with_last_data=True)
    else:
        kw = dict(overwrite_existing_data=True)
    scheduler.experiment.attach_data(
        Data(
            df=pd.DataFrame.from_records(
                dict(
                    trial_index=[idx for trial_results in metric_data.values() for idx in trial_results.keys()],
                    arm_name=[f"{idx}_0" for trial_results in metric_data.values() for idx in trial_results.keys()],
                    metric_name=[metric for metric, trial_results in metric_data.items() for _ in trial_results],
                    mean=[val for trial_results in metric_data.values() for val in trial_results.values()],
                    sem=0.0,
                )
            )
        ),
        **kw,
    )


def get_config_options(script_options: dict = None):
    script_options = script_options if script_options is not None else {}
    append_timestamp = (
        script_options.get("append_timestamp", None)
        if script_options.get("append_timestamp", None) is not None
        else fields_dict(BOAScriptOptions)["append_timestamp"].default
    )

    working_dir = script_options.get("working_dir", fields_dict(BOAScriptOptions)["working_dir"].default)
    working_dir = _prepend_rel_path(os.getcwd(), working_dir)

    if working_dir:
        sys.path.append(str(working_dir))

    return dict(
        append_timestamp=append_timestamp,
        working_dir=working_dir,
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
