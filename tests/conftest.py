import os
from functools import partial
from pathlib import Path

import pytest
from scripts.run import main

from boa import cd_and_cd_back, load_experiment_config


@pytest.fixture
def synth_config():
    config_path = Path(__file__).parent / "test_configs/test_config_synth.yaml"
    return load_experiment_config(config_path)


@pytest.fixture
def metric_config():
    config_path = Path(__file__).parent / "test_configs/test_config_metric.yaml"
    return load_experiment_config(config_path)


@pytest.fixture
def gen_strat1_config():
    config_path = Path(__file__).parent / "test_configs/test_config_gen_strat1.yaml"
    return load_experiment_config(config_path)


@pytest.fixture
def soo_config():
    """ScalarizedObjective Optimization config"""
    config_path = Path(__file__).parent / "test_configs/test_config_soo.yaml"
    return load_experiment_config(config_path)


@pytest.fixture
def moo_config():
    """MultiObjective Optimization config"""
    config_path = Path(__file__).parent / "test_configs/test_config_moo.yaml"
    return load_experiment_config(config_path)


@pytest.fixture
def synth_optimization_options(synth_config):
    return synth_config["optimization_options"]


@pytest.fixture
def metric_optimization_options(metric_config):
    return metric_config["optimization_options"]


@pytest.fixture
def cd_to_root_and_back():
    with cd_and_cd_back(Path(__file__).resolve().parent.parent):
        yield


@pytest.fixture(scope="session")
def cd_to_root_and_back_session():
    with cd_and_cd_back(Path(__file__).resolve().parent.parent):
        yield


@pytest.fixture(scope="session")
def script_main_run(tmp_path_factory, cd_to_root_and_back_session):
    output_dir = tmp_path_factory.mktemp("output")
    yield main(output_dir)
