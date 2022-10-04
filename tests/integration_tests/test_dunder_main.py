def test_calling_command_line_python_test_script_doesnt_error_out_and_produces_correct_no_of_trials(
    stand_alone_opt_package_run,
):
    scheduler = stand_alone_opt_package_run
    wrapper = scheduler.experiment.runner.wrapper
    config = wrapper.config
    total_trials = config["optimization_options"]["scheduler"]["total_trials"]
    assert len(scheduler.experiment.trials) == total_trials


def test_calling_command_line_r_test_scripts(r_scripts_run):
    scheduler = r_scripts_run
    wrapper = scheduler.experiment.runner.wrapper
    config = wrapper.config
    total_trials = config["optimization_options"]["scheduler"]["total_trials"]
    assert len(scheduler.experiment.trials) == total_trials
