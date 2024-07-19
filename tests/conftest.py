import json
import logging
import os
from pathlib import Path

import pytest

import boa.scripts.moo as run_moo
import boa.scripts.run_branin as run_branin
from boa import BOAConfig, cd_and_cd_back, split_shell_command
from boa.cli import main as cli_main
from boa.definitions import ROOT, TEST_SCRIPTS_DIR

logger = logging.getLogger(__file__)

TEST_DIR = ROOT / "tests"
TEST_CONFIG_DIR = TEST_DIR / "test_configs"
TEST_DEPRECATED_CONFIG_DIR = TEST_DIR / "test_configs/deprecated_configs"


@pytest.fixture
def generic_config():
    config_path = TEST_CONFIG_DIR / "test_config_generic.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def saasbo_config():
    config_path = TEST_CONFIG_DIR / "test_config_saasbo.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def moo_config():
    """MultiObjective Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_moo.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def scripts_moo():
    """PassThrough Optimization config"""
    config_path = TEST_SCRIPTS_DIR / "moo.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def scripts_synth_func():
    """PassThrough Optimization config"""
    config_path = TEST_SCRIPTS_DIR / "synth_func_config.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def denormed_param_parse_config():
    """MultiObjective Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_param_parse.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def denormed_custom_wrapper_config_path():
    """MultiObjective Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_param_parse_with_wrapper_load.yaml"
    return config_path


@pytest.fixture
def pass_through_config():
    """PassThrough Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_pass_through_metric.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def soo_config():
    """ScalarizedObjective Optimization config"""
    config_path = TEST_CONFIG_DIR / "test_config_soo.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def gen_strat1_config():
    config_path = TEST_CONFIG_DIR / "test_config_gen_strat1.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def synth_config():
    config_path = TEST_CONFIG_DIR / "test_config_synth.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


######################
# Deprecated Configs #
######################

# Only tested in test_config_deprecation_normalization.py, which tests
# the deprecation normalization process


@pytest.fixture
def pass_through_config_deprecated():
    """PassThrough Optimization config"""
    config_path = TEST_DEPRECATED_CONFIG_DIR / "test_config_pass_through_metric_deprecated.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def soo_config_deprecated():
    """ScalarizedObjective Optimization config"""
    config_path = TEST_DEPRECATED_CONFIG_DIR / "test_config_soo_deprecated.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def metric_config_deprecated():
    config_path = TEST_DEPRECATED_CONFIG_DIR / "test_config_metric_deprecated.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def gen_strat1_config_deprecated():
    config_path = TEST_DEPRECATED_CONFIG_DIR / "test_config_gen_strat1_deprecated.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def synth_config_deprecated():
    config_path = TEST_DEPRECATED_CONFIG_DIR / "test_config_synth_deprecated.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def moo_config_deprecated():
    """MultiObjective Optimization config"""
    config_path = TEST_DEPRECATED_CONFIG_DIR / "test_config_moo_deprecated.yaml"
    return BOAConfig.from_jsonlike(file=config_path)


@pytest.fixture
def cd_to_root_and_back():
    with cd_and_cd_back(ROOT):
        yield


@pytest.fixture(scope="session")
def cd_to_root_and_back_session():
    with cd_and_cd_back(ROOT):
        yield


@pytest.fixture(scope="session")
def denormed_custom_wrapper_run(tmp_path_factory, cd_to_root_and_back_session):
    config = {
        "objective": {"metrics": [{"name": "metric"}]},
        "params": {
            "a": {
                "x1": {"type": "range", "bounds": [0, 1], "value_type": "float"},
                "x2": {"type": "fixed", "value": 0.5, "value_type": "float"},
            },
            "b": {
                "x1": {"type": "range", "bounds": [0, 1], "value_type": "float"},
                "x2": {"type": "fixed", "value": 0.5, "value_type": "float"},
            },
        },
        "params_a": {
            "x1": {"dummy_key": "dummy_value", "type": "range", "bounds": [0, 1], "value_type": "float"},
            "x2": {"dummy_key": "dummy_value", "type": "fixed", "value": 0.5, "value_type": "float"},
        },
        "params2": [
            {
                "a": {
                    "x1": {"type": "range", "bounds": [0, 1], "value_type": "float"},
                    "x2": {"type": "fixed", "value": 0.5, "value_type": "float"},
                }
            },
            {
                "b": {
                    "x1": {"type": "range", "bounds": [0, 1], "value_type": "float"},
                    "x2": {"type": "fixed", "value": 0.5, "value_type": "float"},
                }
            },
        ],
        "scheduler": {"n_trials": 5},
        "script_options": {
            "wrapper_name": "WrapperConfigNormalization",
            "wrapper_path": str((TEST_DIR / "integration_tests/test_storage.py").resolve()),
        },
    }
    temp_dir = tmp_path_factory.mktemp("temp_dir")
    config_path = temp_dir / "different_name_config.json"
    with open(Path(config_path), "w") as file:
        json.dump(config, file)
    scheduler = cli_main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)
    os.remove(config_path)
    yield scheduler


@pytest.fixture(scope="session")
def branin_main_run(tmp_path_factory, cd_to_root_and_back_session):
    yield run_branin.main()


@pytest.fixture(scope="session")
def moo_main_run(tmp_path_factory, cd_to_root_and_back_session):
    yield run_moo.main()


@pytest.fixture(scope="session")
def stand_alone_opt_package_run(tmp_path_factory, cd_to_root_and_back_session):
    config_path = TEST_DIR / "scripts/stand_alone_opt_package/stand_alone_pkg_config.yaml"
    args = f"--config-path {config_path} -td"
    yield cli_main(split_shell_command(args), standalone_mode=False)


@pytest.fixture(scope="session")
def r_full(tmp_path_factory, cd_to_root_and_back_session):
    config_path = TEST_DIR / f"scripts/other_langs/r_package_full/config.yaml"

    yield cli_main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)


@pytest.fixture(scope="session")
def r_light(tmp_path_factory, cd_to_root_and_back_session):
    config_path = TEST_DIR / f"scripts/other_langs/r_package_light/config.yaml"

    yield cli_main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)


@pytest.fixture(scope="session")
def r_streamlined(tmp_path_factory, cd_to_root_and_back_session):
    config_path = TEST_DIR / f"scripts/other_langs/r_package_streamlined/config.yaml"

    yield cli_main(split_shell_command(f"--config-path {config_path} -td"), standalone_mode=False)
