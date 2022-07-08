from boa import get_metric_from_config, get_trial_dir


def test_exp_dir_exists(script_main_run):
    scheduler, config = script_main_run

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    assert experiment_dir.exists()


def test_trial_dir_exists(script_main_run):
    scheduler, config = script_main_run

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    for trial_index in range(config["optimization_options"]["scheduler"]["total_trials"]):
        assert (get_trial_dir(experiment_dir, trial_index)).exists()


def test_output_file_exists(script_main_run):
    scheduler, config = script_main_run

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    for trial_index in range(config["optimization_options"]["scheduler"]["total_trials"]):
        assert (get_trial_dir(experiment_dir, trial_index) / "output.json").exists()


def test_df(script_main_run):
    scheduler, config = script_main_run
    config_metric = config["optimization_options"]["objective_options"]["objectives"][0]

    df = scheduler.experiment.fetch_data().df
    metric = get_metric_from_config(config_metric)
    assert df["metric_name"].unique()[0] == metric.name
    assert df["sem"].unique()[0] == config_metric["noise_sd"]
    assert len(df) == config["optimization_options"]["scheduler"]["total_trials"]
