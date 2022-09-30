from unittest import TestCase

from boa import boa_params_to_wpr, normalize_config


def test_wpr_params_to_boa(denormed_param_parse_config):
    parameter_keys = denormed_param_parse_config["optimization_options"]["parameter_keys"]
    config = normalize_config(denormed_param_parse_config, parameter_keys)
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
    for key in config["parameters"]:
        assert key["name"] in names
    assert len(config["parameters"]) == len(names)


def test_boa_params_to_wpr(denormed_param_parse_config):
    parameter_keys = denormed_param_parse_config["optimization_options"]["parameter_keys"]
    config = normalize_config(denormed_param_parse_config, parameter_keys)
    orig_params = boa_params_to_wpr(config["parameters"], config["optimization_options"]["mapping"], from_trial=False)

    d = {k: v for k, v in config.items() if k in [keys[0] for keys in parameter_keys]}
    TestCase().assertDictEqual(d, orig_params)
