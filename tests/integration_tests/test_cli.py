import os
import subprocess
from pathlib import Path

import pytest
from ax.service.scheduler import FailureRateExceededError

from boa import (
    BaseWrapper,
    BOAConfig,
    cd_and_cd_back,
    get_trial_dir,
    load_jsonlike,
    scheduler_from_json_file,
    split_shell_command,
)
from boa.cli import main as cli_main
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


class WrapperDunderMain(BaseWrapper):
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
# the botorch modular version is the same as the streamlined version, but also uses botorch modular
# which uses a custom kernel, acquisition function, mll and botorch model class
# (which can customize the GP process even more)
@pytest.mark.parametrize(
    "r_scripts_run",
    [
        "r_full",
        "r_light",
        "r_streamlined",
        "r_streamlined_botorch_modular",
        pytest.param(
            "r_streamlined_botorch_modular",
            marks=pytest.importorskip(
                "ax-platform",
                minversion="0.3.5",
                reason="BOTORCH_MODULAR model is not available in BOA with Ax version < 0.3.5.",
            ),
        ),
    ],
)
@pytest.mark.skipif(not R_INSTALLED, reason="requires R to be installed")
def test_calling_command_line_r_test_scripts(r_scripts_run, request):
    scheduler = request.getfixturevalue(r_scripts_run)
    wrapper = scheduler.wrapper
    config = wrapper.config
    assert len(scheduler.experiment.trials) == config.trials

    assert scheduler
    if "r_full" == r_scripts_run:
        data = load_jsonlike(get_trial_dir(wrapper.experiment_dir, 0) / "data.json")
        assert "param_names" in data
        assert "metric_properties" in data

    if r_scripts_run in ("r_streamlined", "r_streamlined_botorch_modular"):
        with cd_and_cd_back(scheduler.wrapper.config_path.parent):

            pre_num_trials = len(scheduler.experiment.trials)

            scheduler = scheduler_from_json_file(scheduler.scheduler_filepath)
            scheduler.run_n_trials(5)

            post_num_trials = len(scheduler.experiment.trials)

            # assert some trials run, even if we hit max trials and not all specified trials were run
            assert post_num_trials == pre_num_trials + 5


@pytest.mark.skipif(not R_INSTALLED, reason="requires R to be installed")
def test_cli_interface_with_failing_test_that_sends_back_failed_trial_status():
    with pytest.raises(FailureRateExceededError):
        config_path = ROOT / "tests" / f"scripts/other_langs/r_package_streamlined/config_fail.yaml"
        cli_main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)


@pytest.mark.skipif(not R_INSTALLED, reason="requires R to be installed")
def test_cli_interface_with_failing_test_that_sends_back_failed_trial_status():
    with pytest.raises(FailureRateExceededError):
        config_path = ROOT / "tests" / f"scripts/other_langs/r_pass_back_fail_trial_status/config.yaml"
        cli_main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)


def test_wrapper_with_custom_load_config():
    # This should fail with a failing config
    config_path = ROOT / "tests" / f"scripts/other_langs/r_package_streamlined/config_fail.yaml"
    # But we override the failing config in our wrapper with a working one in a custom load_config
    wrapper_path = Path(__file__)
    cli_main(
        split_shell_command(
            f"--config-path {config_path}"
            f" --wrapper-path {wrapper_path}"
            f" --wrapper-name {WrapperDunderMain.__name__}"
            " -td"
        ),
        standalone_mode=False,
    )


def test_parallelism(r_light, caplog):
    scheduler = r_light
    log_f = scheduler.wrapper.experiment_dir / "optimization.log"
    with open(log_f, "r") as f:
        log = f.readlines()
    log = [line.strip() for line in log if "R script" in line]

    found_parallelism = False
    for line in range(len(log) - 1):
        if "R script started running." in log[line] and "R script started running." in log[line + 1]:
            found_parallelism = True
    assert found_parallelism


def test_non_zero_exit_code_fails_trial():
    with pytest.raises(FailureRateExceededError):
        config_path = ROOT / "tests" / f"scripts/other_langs/r_failure_exit_code/config.yaml"
        cli_main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)


def test_return_nan_fails_trial():
    with pytest.raises(FailureRateExceededError):
        config_path = ROOT / "tests" / f"scripts/other_langs/r_failure_nan/config.yaml"
        cli_main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)
