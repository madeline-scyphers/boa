from boa import BOAConfig, get_metric_from_config, get_trial_dir


def test_exp_dir_exists(branin_main_run):
    scheduler = branin_main_run

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    assert experiment_dir.exists()


def test_trial_dir_exists(branin_main_run):
    scheduler = branin_main_run
    config = scheduler.runner.wrapper.config

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    # we leave off 5 trials from total trials for the save load test below
    for trial_index in range(config.scheduler.total_trials - 5):
        assert (get_trial_dir(experiment_dir, trial_index)).exists()


def test_output_file_exists(branin_main_run):
    scheduler = branin_main_run
    config = scheduler.runner.wrapper.config

    experiment_dir = scheduler.experiment.runner.wrapper.experiment_dir
    # we leave off 5 trials from total trials for the save load test below
    for trial_index in range(config.scheduler.total_trials - 5):
        assert (get_trial_dir(experiment_dir, trial_index) / "output.json").exists()


def test_df(branin_main_run):
    scheduler = branin_main_run
    config: BOAConfig = scheduler.runner.wrapper.config
    config_metric = config.objective.metrics[0]

    df = scheduler.experiment.fetch_data().df
    metric = get_metric_from_config(config_metric)
    assert df["metric_name"].unique()[0] == metric.name
    assert df["sem"].unique()[0] == config_metric.noise_sd
    # we leave off 5 trials from total trials for a different save load test
    assert len(df) == config.scheduler.total_trials - 5
