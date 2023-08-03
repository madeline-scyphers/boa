import json
import logging
from pathlib import Path

import pytest

import boa.__main__ as dunder_main
import boa.scripts.moo as run_moo
import boa.scripts.run_branin as run_branin
from boa import cd_and_cd_back, load_yaml, split_shell_command
from boa.definitions import ROOT

logger = logging.getLogger(__file__)

TEST_DIR = ROOT / "tests"
TEST_CONFIG_DIR = TEST_DIR / "test_configs"


@pytest.fixture
def synth_config():
    config_path = TEST_CONFIG_DIR / "test_config_synth.yaml"
    return load_yaml(config_path)


@pytest.fixture
def generic_config():
    config_path = TEST_CONFIG_DIR / "test_config_generic.yaml"
    return load_yaml(config_path, normalize=False)


@pytest.fixture
def metric_config():
    config_path = TEST_CONFIG_DIR / "test_config_metric.yaml"
    return load_yaml(config_path)


@pytest.fixture
def gen_strat1_config():
    config_path = TEST_CONFIG_DIR / "test_config_gen_strat1.yaml"
    return load_yaml(config_path)


@pytest.fixture
def soo_config():
    """ScalarizedObjective Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_soo.yaml"
    return load_yaml(config_path)


@pytest.fixture
def moo_config():
    """MultiObjective Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_moo.yaml"
    return load_yaml(config_path)


@pytest.fixture
def pass_through_config():
    """PassThrough Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_pass_through_metric.yaml"
    return load_yaml(config_path)


@pytest.fixture
def denormed_param_parse_config():
    """MultiObjective Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_param_parse.yaml"
    return load_yaml(config_path)


@pytest.fixture
def synth_optimization_options(synth_config):
    return synth_config["optimization_options"]


@pytest.fixture
def metric_optimization_options(metric_config):
    return metric_config["optimization_options"]


@pytest.fixture
def cd_to_root_and_back():
    with cd_and_cd_back(ROOT):
        yield


@pytest.fixture(scope="session")
def cd_to_root_and_back_session():
    with cd_and_cd_back(ROOT):
        yield


@pytest.fixture(scope="session")
def branin_main_run(tmp_path_factory, cd_to_root_and_back_session):
    yield run_branin.main()


@pytest.fixture(scope="session")
def moo_main_run(tmp_path_factory, cd_to_root_and_back_session):
    yield run_moo.main()


@pytest.fixture(scope="session")
def stand_alone_opt_package_run(request, tmp_path_factory, cd_to_root_and_back_session):
    # parametrize the test to pass in script options in config as relative and absolute paths
    if getattr(request, "param", None) == "absolute":
        wrapper_path = (TEST_DIR / "scripts/stand_alone_opt_package/wrapper.py").resolve()
        config = {
            "optimization_options": {
                "generation_strategy": {
                    "steps": [{"model": "SOBOL", "num_trials": 2}, {"model": "GPEI", "num_trials": -1}]
                },
                "objective_options": {
                    "objectives": [{"metric": "mean", "name": "Mean"}, {"metric": "RMSE", "info_only": True}]
                },
                "trials": 5,
            },
            "parameters": [
                {"bounds": [-5.0, 10.0], "name": "x0", "type": "range"},
                {"bounds": [0.0, 15.0], "name": "x1", "type": "range"},
            ],
            "script_options": {"wrapper_path": str(wrapper_path)},
        }
        temp_dir = tmp_path_factory.mktemp("temp_dir")
        config_path = temp_dir / "config.yaml"
        with open(Path(config_path), "w") as file:
            json.dump(config, file)
    else:
        config_path = TEST_DIR / "scripts/stand_alone_opt_package/stand_alone_pkg_config.yaml"

    yield dunder_main.main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)


@pytest.fixture(scope="session")
def r_scripts_run(request, tmp_path_factory, cd_to_root_and_back_session):
    sub_dir = request.param
    config_path = TEST_DIR / f"scripts/other_langs/r_package_{sub_dir}/config.yaml"

    yield dunder_main.main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)
