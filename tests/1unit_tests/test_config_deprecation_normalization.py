from boa import BOAConfig


def test_config_deprecation_normalization(
    synth_config,
    metric_config,
    gen_strat1_config,
    soo_config,
    moo_config,
    pass_through_config,
    scripts_moo,
    scripts_synth_func,
):
    for config in [synth_config, metric_config, gen_strat1_config, soo_config, moo_config, pass_through_config]:
        assert isinstance(config, BOAConfig)
