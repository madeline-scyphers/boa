from unittest import TestCase

import pytest

from boa import BOAConfig


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


def test_config_run_cmd_sets_to_run_model():
    config = {
        "objective": {"metrics": [{"name": "a"}]},
        "parameters": {"x": 10},
        "n_trials": 1,
        "script_options": {"run_cmd": "some command"},
    }
    c = BOAConfig(**config)
    assert c.script_options.run_model == "some command"


def test_config_run_cmd_and_run_model_error():
    config = {
        "objective": {"metrics": [{"name": "a"}]},
        "parameters": {"x": 10},
        "n_trials": 1,
        "script_options": {
            "run_cmd": "some command",
            "run_model": "some command",
        },
    }
    with pytest.raises(TypeError):
        BOAConfig(**config)


def test_config_weights_can_be_set_on_obj_passed_to_metrics():
    weights = [1, 2]
    config = {
        "objective": {"metrics": [{"name": "a"}, {"name": "b"}], "weights": weights},
        "parameters": {"x": 10},
        "n_trials": 1,
        "script_options": {"run_cmd": "some command"},
    }
    c = BOAConfig(**config)
    for metric, weight in zip(c.objective.metrics, weights):
        assert metric.weight == weight


def test_config_obj_weights_and_metric_weights_error():
    weights = [1, 2]
    config = {
        "objective": {"metrics": [{"name": "a", "weight": 1}, {"name": "b", "weight": 2}], "weights": weights},
        "parameters": {"x": 10},
        "n_trials": 1,
        "script_options": {"run_cmd": "some command"},
    }
    with pytest.raises(TypeError):
        BOAConfig(**config)
