# weird file name with dash in it because CLI conventions
import os
import sys
import tempfile
from pathlib import Path

import click
import pandas as pd
from attrs import fields_dict

from boa.ax_api import TrialStatus
from boa.config import BOAConfig, BOAScriptOptions
from boa.controller import Controller
from boa.storage import client_from_json_file
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
    "-cp",
    "--client-path",
    type=click.Path(),
    default="",
    help="Path to client json file.",
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
    " This is also only done for initial run, not for reloading from client json file.",
)
def main(config_path, client_path, num_trials, temporary_dir):
    if temporary_dir:
        with tempfile.TemporaryDirectory() as temp_dir:
            return run(
                config_path=config_path,
                client_path=client_path,
                num_trials=num_trials,
                experiment_dir=Path(temp_dir),
            )
    return run(
        config_path=config_path,
        client_path=client_path,
        num_trials=num_trials,
    )


def run(config_path, client_path, num_trials, experiment_dir=None):
    experiment_dir = Path(experiment_dir).resolve() if experiment_dir else None
    config_kw = dict(n_trials=num_trials) if num_trials else {}

    if client_path:
        client = client_from_json_file(filepath=Path(client_path).resolve())
        if client.wrapper is None:
            raise ValueError("Loaded client does not have a BOA wrapper attached.")
        config = client.wrapper.config
        if num_trials:
            config.n_trials = num_trials
    else:
        config = BOAConfig.from_jsonlike(config_path, **config_kw)
        if experiment_dir:
            config.script_options.experiment_dir = experiment_dir
        controller = Controller(config_path=config_path, wrapper=SyntheticWrapper(config=config))
        controller.initialize_client()
        client = controller.client

    if client.optimization_csv.exists():
        exp_attach_data_from_opt_csv(list(client.experiment.metrics.keys()), client)

    n_trials = num_trials or config.n_trials
    if n_trials is None:
        raise ValueError("Async optimization requires `num_trials` or `n_trials`.")
    generate_pending_trials(client=client, n_trials=n_trials)
    client.save_data(metrics_to_end=True)
    return client


def generate_pending_trials(client, n_trials: int):
    new_trials = []
    for _ in range(n_trials):
        generator_runs = client.generation_strategy.gen(
            experiment=client.experiment,
            n=1,
            num_trials=1,
        )
        if not generator_runs:
            break
        trial = client.experiment.new_trial(generator_run=generator_runs[0][0])
        new_trials.append(trial)
    for trial in new_trials:
        trial.mark_running(no_runner_required=True)


def exp_attach_data_from_opt_csv(metric_names, client):
    df = pd.read_csv(client.optimization_csv)
    if not set(metric_names).issubset(df.columns):
        return
    ready = df[metric_names].notna().all(axis=1)
    if not ready.any():
        return
    for _, row in df.loc[ready].iterrows():
        trial_index = int(row["trial_index"])
        if trial_index not in client.experiment.trials:
            continue
        trial = client.experiment.trials[trial_index]
        if trial.status == TrialStatus.COMPLETED:
            continue
        raw_data = {metric: float(row[metric]) for metric in metric_names}
        client.attach_data(trial_index=trial_index, raw_data=raw_data)
        trial.mark_completed(unsafe=True)


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
