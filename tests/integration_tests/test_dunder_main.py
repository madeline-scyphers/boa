import subprocess

import pytest
from ax.service.scheduler import FailureRateExceededError

import boa.__main__ as dunder_main
from boa import split_shell_command
from boa.definitions import ROOT

try:
    subprocess.check_call(["R", "--version"])
    json_installed = subprocess.check_output(  # check if necessary R packages are installed
        split_shell_command("""Rscript -e '"jsonlite" %in% rownames(installed.packages())'""")
    )
    if "false" in json_installed.decode("UTF-8").lower():
        R_INSTALLED = False
    else:
        R_INSTALLED = True
except subprocess.CalledProcessError:
    R_INSTALLED = False

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
    assert len(scheduler.experiment.trials) == config.trials


# parametrize the test to use the full version (all scripts) or the light version (only run_model.R)
# or parametrize the test to use the streamlined version (doesn't use trial_status.json, only use output.json)
@pytest.mark.parametrize(
    "r_scripts_run",
    ["full", "light", "streamlined"],
    indirect=True,
)
@pytest.mark.skipif(not R_INSTALLED, reason="requires R to be installed")
def test_calling_command_line_r_test_scripts(r_scripts_run):
    scheduler = r_scripts_run
    wrapper = scheduler.experiment.runner.wrapper
    config = wrapper.config
    assert len(scheduler.experiment.trials) == config.trials


@pytest.mark.skipif(not R_INSTALLED, reason="requires R to be installed")
def test_cli_interface_with_failing_test_that_sends_back_failed_trial_status():
    with pytest.raises(FailureRateExceededError):
        config_path = ROOT / "tests" / f"scripts/other_langs/r_package_streamlined/config_fail.yaml"
        dunder_main.main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)
