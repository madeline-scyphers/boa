import pytest


# parametrize the test to pass in script options in config as relative and absolute paths
@pytest.mark.parametrize(
    "stand_alone_opt_package_run",
    ["relative", "absolute"],
    indirect=True,
)
def test_calling_command_line_test_script_doesnt_error_out_and_produces_correct_no_of_trials(
    stand_alone_opt_package_run,
):
    scheduler = stand_alone_opt_package_run
    wrapper = scheduler.experiment.runner.wrapper
    config = wrapper.config
    total_trials = config["optimization_options"]["scheduler"]["total_trials"]
    assert len(scheduler.experiment.trials) == total_trials


# parametrize the test to use the full version (all scripts) or the light version (only run_model.R)
@pytest.mark.parametrize(
    "r_scripts_run",
    ["full", "light"],
    indirect=True,
)
def test_calling_command_line_r_test_scripts(r_scripts_run):
    scheduler = r_scripts_run
    wrapper = scheduler.experiment.runner.wrapper
    config = wrapper.config
    total_trials = config["optimization_options"]["scheduler"]["total_trials"]
    assert len(scheduler.experiment.trials) == total_trials
