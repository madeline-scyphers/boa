import pytest

from boa import BOAConfig


@pytest.mark.parametrize(
    "config",
    [
        "synth_config_deprecated",
        "metric_config_deprecated",
        "gen_strat1_config_deprecated",
        "soo_config_deprecated",
        "moo_config_deprecated",
        "pass_through_config_deprecated",
    ],  # 1. pass fixture name as a string
)
def test_config_deprecation_normalization(config, request):
    config = request.getfixturevalue(config)
    assert isinstance(config, BOAConfig)
