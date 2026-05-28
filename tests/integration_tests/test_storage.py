import json
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pytest

from boa import (
    BaseWrapper,
    BOAConfig,
    load_jsonlike,
    client_from_json_file as scheduler_from_json_file,
    client_to_json_file as scheduler_to_json_file,
    split_shell_command,
)
from boa.__version__ import __version__
from boa.ax_api import (
    CORE_CLASS_DECODER_REGISTRY,
    CORE_CLASS_ENCODER_REGISTRY,
    CORE_DECODER_REGISTRY,
    CORE_ENCODER_REGISTRY,
    Experiment,
    Objective,
    OptimizationConfig,
    object_from_json,
    object_to_json,
)
from boa.cli import main as cli_main
from boa.definitions import ROOT

TEST_DIR = ROOT / "tests"


class WrapperConfigNormalization(BaseWrapper):
    def load_config(self, config_path, *args, **kwargs) -> BOAConfig:
        config = load_jsonlike(config_path)
        parameter_keys = [
            ["params", "a"],
            ["params", "b"],
            ["params_a"],
            ["params2", 0, "a"],
            ["params2", 1, "b"],
        ]
        assert "dummy_key" in config["params_a"]["x1"]
        assert "dummy_key" in config["params_a"]["x2"]
        config["params_a"]["x1"].pop("dummy_key")
        config["params_a"]["x2"].pop("dummy_key")
        return BOAConfig(parameter_keys=parameter_keys, **config)

    def run_model(self, trial) -> None:
        """"""

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(self, **kwargs) -> dict:
        return 1


@pytest.mark.parametrize(
    "config",
    [
        "generic_config",
        "synth_config",
        "gen_strat1_config",
        "soo_config",
        "moo_config",
        "pass_through_config",
        "scripts_moo",
        "scripts_synth_func",
    ],  # 1. pass fixture name as a string
)
def test_save_load_config(config, request):
    config = request.getfixturevalue(config)
    serialized = object_to_json(
        config,
        encoder_registry=CORE_ENCODER_REGISTRY,
        class_encoder_registry=CORE_CLASS_ENCODER_REGISTRY,
    )

    c = object_from_json(
        serialized,
        decoder_registry=CORE_DECODER_REGISTRY,
        class_decoder_registry=CORE_CLASS_DECODER_REGISTRY,
    )
    assert config == BOAConfig(**c)


def test_config_param_parse_with_custom_wrapper_load_config(denormed_custom_wrapper_run, tmp_path):
    scheduler = denormed_custom_wrapper_run
    file_out = tmp_path / "client.json"
    scheduler_to_json_file(scheduler, file_out)

    scheduler = scheduler_from_json_file(file_out, wrapper=scheduler.wrapper)
    config = scheduler.wrapper.config
    names = {
        "params_a_x2",
        "params_a_x1",
        "params_b_x1",
        "params_b_x2",
        "params_a_x1_0",
        "params_a_x2_0",
        "params2_0_a_x1",
        "params2_0_a_x2",
        "params2_1_b_x1",
        "params2_1_b_x2",
    }
    for key in config.parameters:
        assert key["name"] in names


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Windows doesn't support moving files that are open")
def test_custom_wrapper_load_config_reload_from_moved_files(denormed_custom_wrapper_run, tmp_path):
    scheduler = denormed_custom_wrapper_run
    output_dir = tmp_path / "output_dir"
    copied_config_path = Path(scheduler.wrapper.experiment_dir) / Path(scheduler.wrapper.config_path).name
    shutil.move(scheduler.wrapper.experiment_dir, output_dir)
    moved_config_path = output_dir / copied_config_path.name

    scheduler = scheduler_from_json_file(output_dir / "client.json", wrapper=scheduler.wrapper)
    config = scheduler.wrapper.config
    names = {
        "params_a_x2",
        "params_a_x1",
        "params_b_x1",
        "params_b_x2",
        "params_a_x1_0",
        "params_a_x2_0",
        "params2_0_a_x1",
        "params2_0_a_x2",
        "params2_1_b_x1",
        "params2_1_b_x2",
    }
    for key in config.parameters:
        assert key["name"] in names

    os.remove(moved_config_path)
    scheduler = scheduler_from_json_file(output_dir / "client.json", wrapper=scheduler.wrapper)
    config = scheduler.wrapper.config
    for key in config.parameters:
        assert key["name"] in names


def test_save_load_scheduler_branin(branin_main_run, tmp_path):
    file_out = tmp_path / "client.json"
    scheduler = branin_main_run
    scheduler_to_json_file(scheduler, file_out)

    pre_num_trials = len(scheduler.experiment.trials)

    scheduler = scheduler_from_json_file(file_out)
    scheduler.run_n_trials(5)

    post_num_trials = len(scheduler.experiment.trials)

    # assert some trials run, even if we hit max trials and not all specified trials were run
    assert post_num_trials > pre_num_trials


def test_can_pass_custom_wrapper_path_when_loading_scheduler(branin_main_run, tmp_path):
    file_out = tmp_path / "client.json"
    scheduler = branin_main_run

    orig_wrapper_path = scheduler.experiment.runner.wrapper._path
    scheduler.experiment.runner.wrapper._path = "SOME/OTHER/PATH"

    scheduler_to_json_file(scheduler, file_out)

    pre_num_trials = len(scheduler.experiment.trials)

    scheduler = scheduler_from_json_file(file_out, wrapper_path=orig_wrapper_path)
    scheduler.run_n_trials(5)

    post_num_trials = len(scheduler.experiment.trials)

    # assert some trials run, even if we hit max trials and not all specified trials were run
    assert post_num_trials == pre_num_trials + 5


def test_can_pass_custom_wrapper_path_when_loading_scheduler_from_cli(stand_alone_opt_package_run, tmp_path_factory):
    scheduler = stand_alone_opt_package_run

    temp_dir = tmp_path_factory.mktemp("temp_dir")
    file_out = temp_dir / "client.json"

    orig_wrapper_path = scheduler.experiment.runner.wrapper._path
    scheduler.experiment.runner.wrapper._path = "SOME/OTHER/PATH"

    scheduler_to_json_file(scheduler, file_out)

    pre_num_trials = len(scheduler.experiment.trials)

    scheduler = cli_main(
        split_shell_command(f"--client-path {file_out} --wrapper-path {orig_wrapper_path} -td"),
        standalone_mode=False,
    )

    scheduler.run_n_trials(5)

    post_num_trials = len(scheduler.experiment.trials)

    # post should be 2 * pre + 5 because we ran opt twice and then ran 5 more trials
    assert post_num_trials == 2 * pre_num_trials + 5


def test_boa_version_in_scheduler(stand_alone_opt_package_run, tmp_path_factory):
    scheduler = stand_alone_opt_package_run

    temp_dir = tmp_path_factory.mktemp("temp_dir")
    file_out = temp_dir / "client.json"

    scheduler_to_json_file(scheduler, file_out)
    with open(file_out, "r") as f:
        scheduler_json = json.load(f)

    assert "boa_version" in scheduler_json
    assert scheduler_json["boa_version"] == __version__
