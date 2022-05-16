import pytest
from pathlib import Path

from optiwrap import load_experiment_config
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
def run_script_main():
    return main
