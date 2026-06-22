from unittest import TestCase

import pytest

from boa import BOAConfig
from boa.ax_api import ScalarizedObjective, optimization_config_from_string


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
        "params2_0_a_x1",
        "params2_0_a_x2",
        "params2_1_b_x1",
        "params2_1_b_x2",
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
        "optimization": {"objective": "a", "metrics": {"a": {"name": "a", "metric_type": "passthrough"}}},
        "parameters": {"x": 10},
        "n_trials": 1,
        "script_options": {"run_cmd": "some command"},
    }
    c = BOAConfig(**config)
    assert c.script_options.run_model == "some command"


def test_config_run_cmd_and_run_model_error():
    config = {
        "optimization": {"objective": "a", "metrics": {"a": {"name": "a", "metric_type": "passthrough"}}},
        "parameters": {"x": 10},
        "n_trials": 1,
        "script_options": {
            "run_cmd": "some command",
            "run_model": "some command",
        },
    }
    with pytest.raises(TypeError):
        BOAConfig(**config)


def test_config_weighted_objective_expression_configures_scalarized_objective():
    config = {
        "optimization": {
            "objective": "-a - 2*b",
            "metrics": {
                "a": {"name": "a", "metric_type": "passthrough"},
                "b": {"name": "b", "metric_type": "passthrough"},
            },
        },
        "parameters": {"x": 10},
        "n_trials": 1,
        "script_options": {"run_cmd": "some command"},
    }
    c = BOAConfig(**config)
    optimization_config = optimization_config_from_string(objective_str=c.optimization.objective)
    assert isinstance(optimization_config.objective, ScalarizedObjective)
    assert optimization_config.objective.weights == [-1.0, -2.0]


def test_config_obj_weights_and_metric_weights_error():
    weights = [1, 2]
    config = {
        "optimization": {
            "objective": "-a - 2*b",
            "weights": weights,
            "metrics": {
                "a": {"name": "a", "weight": 1, "metric_type": "passthrough"},
                "b": {"name": "b", "weight": 2, "metric_type": "passthrough"},
            },
        },
        "parameters": {"x": 10},
        "n_trials": 1,
        "script_options": {"run_cmd": "some command"},
    }
    with pytest.raises(TypeError):
        BOAConfig(**config)
