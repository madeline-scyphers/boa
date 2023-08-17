from boa import BOAConfig
from tests.conftest import TEST_CONFIG_DIR


def test_config_instantiation():
    BOAConfig.from_jsonlike(TEST_CONFIG_DIR / "test_config_generic.yaml")
