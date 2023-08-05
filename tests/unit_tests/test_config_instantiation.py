from boa import Config
from tests.conftest import TEST_CONFIG_DIR


def test_config_instantiation(generic_config):
    Config.from_jsonlike(TEST_CONFIG_DIR / "test_config_generic.yaml")
    Config(**generic_config)
