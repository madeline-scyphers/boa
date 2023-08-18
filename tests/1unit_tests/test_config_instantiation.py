from boa import BOAConfig
from tests.conftest import TEST_CONFIG_DIR


def test_config_instantiation():
    BOAConfig.from_jsonlike(TEST_CONFIG_DIR / "test_config_generic.yaml")


def test_config_with_jinja2():
    config = BOAConfig.from_jsonlike(TEST_CONFIG_DIR / "test_config_jinja2.yaml")
    assert len(config.parameters) == 13
    assert len(config.parameter_constraints) == 13
