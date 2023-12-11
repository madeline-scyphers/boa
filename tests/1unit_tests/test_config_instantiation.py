from boa import BOAConfig
from boa.definitions import ROOT

TEST_CONFIG_DIR = ROOT / "tests" / "test_configs"


def test_config_instantiation():
    BOAConfig.from_jsonlike(TEST_CONFIG_DIR / "test_config_generic.yaml")
