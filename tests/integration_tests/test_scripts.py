from optiwrap import get_trial_dir, get_metric_from_config


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

    df = scheduler.experiment.fetch_data().df
    metric = get_metric_from_config(config["optimization_options"])
    assert df["metric_name"].unique()[0] == metric.name
    assert df["sem"].unique()[0] == config["optimization_options"]["metric"]["noise_sd"]
    assert len(df) == config["optimization_options"]["scheduler"]["total_trials"]
