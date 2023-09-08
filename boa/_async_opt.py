# weird file name with dash in it because CLI conventions
import dataclasses
import os
import sys
from pathlib import Path

import click
import pandas as pd
from attrs import fields_dict
from ax import Data
from ax.storage.json_store.decoder import object_from_json

from boa.config import BOAConfig, BOAScriptOptions, MetricType
from boa.controller import Controller
from boa.storage import scheduler_from_json_file
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
def main(config_path, scheduler_path, num_trials):
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
        for metric in metrics.keys():
            scheduler.experiment.attach_data(
                Data(
                    df=pd.DataFrame.from_records(
                        dict(
                            trial_index=list(trials.keys()),
                            arm_name=[f"{i}_0" for i in trials.keys()],
                            metric_name=metric,
                            mean=None,
                            sem=0.0,
                        )
                    )
                ),
                combine_with_last_data=True,
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
    for metric, trial_results in new_data[metric_names].to_dict().items():
        scheduler.experiment.attach_data(
            Data(
                df=pd.DataFrame.from_records(
                    dict(
                        trial_index=list(trial_results.keys()),
                        arm_name=[f"{i}_0" for i in trial_results.keys()],
                        metric_name=metric,
                        mean=list(trial_results.values()),
                        sem=0.0,
                    )
                )
            ),
            combine_with_last_data=True,
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
