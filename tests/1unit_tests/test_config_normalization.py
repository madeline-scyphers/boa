from unittest import TestCase


def test_wpr_params_to_boa(denormed_param_parse_config):
    # parameter_keys = denormed_param_parse_config.parameter_keys
    config = denormed_param_parse_config
    # How the parameter names should
    names = {
        "params_a_x2",
        "params_a_x1",
        "params_b_x1",
        "params_b_x2",
        "params_a_x1_0",
        "params_a_x2_0",
        "params2_0_0_x1",
        "params2_0_0_x2",
        "params2_1_0_x1",
        "params2_1_0_x2",
    }
    for key in config.parameters:
        assert key["name"] in names
    assert len(config.parameters) == len(names)


def test_boa_params_to_wpr(denormed_param_parse_config):
    config = denormed_param_parse_config
    # parameter_keys = denormed_param_parse_config.parameter_keys
    orig_params = config.boa_params_to_wpr(config.parameters, config.mapping, from_trial=False)

    d = {k: v for k, v in config.orig_config.items() if k in [keys[0] for keys in config.parameter_keys]}
    TestCase().assertDictEqual(d, orig_params)
