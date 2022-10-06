from pathlib import Path

import pytest

import boa.__main__ as dunder_main
import boa.test_scripts.run_branin as run_branin
from boa import cd_and_cd_back, load_yaml, split_shell_command

ROOT = Path(__file__).parent.parent
TEST_DIR = ROOT / "tests"
TEST_CONFIG_DIR = TEST_DIR / "test_configs"


@pytest.fixture
def synth_config():
    config_path = Path(__file__).parent / "test_configs/test_config_synth.yaml"
    return load_yaml(config_path)


@pytest.fixture
def metric_config():
    config_path = Path(__file__).parent / "test_configs/test_config_metric.yaml"
    return load_yaml(config_path)


@pytest.fixture
def gen_strat1_config():
    config_path = Path(__file__).parent / "test_configs/test_config_gen_strat1.yaml"
    return load_yaml(config_path)


@pytest.fixture
def soo_config():
    """ScalarizedObjective Optimization config"""
    config_path = Path(__file__).parent / "test_configs/test_config_soo.yaml"
    return load_yaml(config_path)


@pytest.fixture
def moo_config():
    """MultiObjective Optimization config"""
    config_path = Path(__file__).parent / "test_configs/test_config_moo.yaml"
    return load_yaml(config_path)


@pytest.fixture
def denormed_param_parse_config():
    """MultiObjective Optimization config"""
    config_path = Path(__file__).parent / "test_configs/test_config_param_parse.yaml"
    return load_yaml(config_path)


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
    yield run_branin.main(split_shell_command(f"--output_dir {output_dir}"), standalone_mode=False)


@pytest.fixture(scope="session")
def stand_alone_opt_package_run(tmp_path_factory, cd_to_root_and_back_session):
    config_path = TEST_DIR / "scripts/stand_alone_opt_package/stand_alone_pkg_config.json"

    yield dunder_main.main(split_shell_command(f"--config_path {config_path} -td"), standalone_mode=False)


@pytest.fixture(scope="session")
def r_scripts_run(tmp_path_factory, cd_to_root_and_back_session):
    config_path = TEST_DIR / "scripts/r_package/config.yaml"

    yield dunder_main.main(split_shell_command(f"--config_path {config_path} -td"), standalone_mode=False)
