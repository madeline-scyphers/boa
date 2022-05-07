import pytest
from pathlib import Path

from optiwrap import load_experiment_config


@pytest.fixture
def config():
    config_path = Path(__file__).parent / "test_config.yaml"
    return load_experiment_config(config_path)

@pytest.fixture
def optimization_options(config):
    return config["optimization_options"]