import pathlib
import subprocess

import pytest
from ax.service.scheduler import FailureRateExceededError

import boa.__main__ as dunder_main
from boa import (
    BaseWrapper,
    BOAConfig,
    get_trial_dir,
    load_jsonlike,
    split_shell_command,
)
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


class Wrapper(BaseWrapper):
    def load_config(self, config_path, *args, **kwargs) -> BOAConfig:
        return BOAConfig(
            objective={"metrics": [{"name": "passthrough"}]},
            params=dict(
                a=dict(x1=dict(bounds=[-5.0, 10.0], type="range")),
                b=dict(x2=dict(bounds=[-5.0, 10.0], type="range")),
            ),
            params_a=dict(x1=dict(bounds=[-5.0, 10.0], type="range"), x2=dict(bounds=[-5.0, 10.0], type="range")),
            parameter_keys=[
                ["params", "a"],
                ["params", "b"],
                ["params_a"],
            ],
            scheduler=dict(n_trials=5),
        )

    def run_model(self, trial) -> None:
        pass

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(self, trial, *args, **kwargs) -> dict:
        return 1 / (trial.index + 1)


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
def test_calling_command_line_r_test_scripts(r_scripts_run, request):
    scheduler = r_scripts_run
    wrapper = scheduler.experiment.runner.wrapper
    config = wrapper.config
    assert len(scheduler.experiment.trials) == config.trials

    assert scheduler
    if "r_package_streamlined" in str(wrapper.config_path):
        assert "param_names" in load_jsonlike(get_trial_dir(wrapper.experiment_dir, 0) / "data.json")


@pytest.mark.skipif(not R_INSTALLED, reason="requires R to be installed")
def test_cli_interface_with_failing_test_that_sends_back_failed_trial_status():
    with pytest.raises(FailureRateExceededError):
        config_path = ROOT / "tests" / f"scripts/other_langs/r_package_streamlined/config_fail.yaml"
        dunder_main.main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)


def test_wrapper_with_custom_load_config():
    # This should fail with a failing config
    config_path = ROOT / "tests" / f"scripts/other_langs/r_package_streamlined/config_fail.yaml"
    # But we override the failing config in our wrapper with a working one in a custom load_config
    wrapper_path = pathlib.Path(__file__)
    dunder_main.main(
        split_shell_command(f"--config-path {config_path} --wrapper-path {wrapper_path} -td"), standalone_mode=False
    )
