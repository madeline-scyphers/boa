import os
from functools import partial

import pytest
from pathlib import Path

from optiwrap import load_experiment_config, cd_and_cd_back
from scripts.run import main


@pytest.fixture
def synth_config():
    config_path = Path(__file__).parent / "test_configs/test_config_synth.yaml"
    return load_experiment_config(config_path)


@pytest.fixture
def metric_config():
    config_path = Path(__file__).parent / "test_configs/test_config_metric.yaml"
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
