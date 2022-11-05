import logging

from boa import (
    get_metric_from_config,
    get_trial_dir,
    scheduler_from_json_file,
    scheduler_to_json_file,
)
from boa.definitions import TEST_SCRIPTS_DIR
from boa.scripts.script_wrappers import Wrapper


def test_exp_dir_exists(script_main_run):
    scheduler, config = script_main_run

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    assert experiment_dir.exists()


def test_trial_dir_exists(script_main_run):
    scheduler, config = script_main_run

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    # we leave off 5 trials from total trials for the save load test below
    for trial_index in range(config["optimization_options"]["scheduler"]["total_trials"] - 5):
        assert (get_trial_dir(experiment_dir, trial_index)).exists()


def test_output_file_exists(script_main_run):
    scheduler, config = script_main_run

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    # we leave off 5 trials from total trials for the save load test below
    for trial_index in range(config["optimization_options"]["scheduler"]["total_trials"] - 5):
        assert (get_trial_dir(experiment_dir, trial_index) / "output.json").exists()


def test_df(script_main_run):
    scheduler, config = script_main_run
    config_metric = config["optimization_options"]["objective_options"]["objectives"][0]

    df = scheduler.experiment.fetch_data().df
    metric = get_metric_from_config(config_metric)
    assert df["metric_name"].unique()[0] == metric.name
    assert df["sem"].unique()[0] == config_metric["noise_sd"]
    # we leave off 5 trials from total trials for the save load test below
    assert len(df) == config["optimization_options"]["scheduler"]["total_trials"] - 5


def test_save_load_scheduler_branin(script_main_run, tmp_path):
    file_out = tmp_path / "scheduler.json"
    scheduler, config = script_main_run
    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    scheduler_to_json_file(scheduler, file_out)

    config_file = TEST_SCRIPTS_DIR / "synth_func_config.yaml"
    wrapper = Wrapper()
    wrapper.load_config(config_path=config_file)
    wrapper.experiment_dir = experiment_dir

    pre_num_trials = len(scheduler.experiment.trials)

    scheduler = scheduler_from_json_file(file_out, wrapper=wrapper)
    scheduler.run_n_trials(5)

    post_num_trials = len(scheduler.experiment.trials)

    # assert some trials run, even if we hit max trials and not all specified trials were run
    assert post_num_trials > pre_num_trials
