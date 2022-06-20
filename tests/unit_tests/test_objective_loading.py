from pprint import pprint

from ax import (
    ComparisonOp,
    Experiment,
    Metric,
    MultiObjective,
    MultiObjectiveOptimizationConfig,
    Objective,
    ObjectiveThreshold,
    OptimizationConfig,
    OutcomeConstraint,
    Runner,
    SearchSpace,
)
from ax.core.objective import ScalarizedObjective

from boa import get_optimization_config


def test_soo_config_loading(soo_config):
    optimization_config = get_optimization_config(soo_config["optimization_options"])
    assert isinstance(optimization_config, OptimizationConfig)

    outcome_constraints = optimization_config.outcome_constraints
    for outcome_constraint in outcome_constraints:
        assert isinstance(outcome_constraint, OutcomeConstraint)

    obj = optimization_config.objective
    assert isinstance(obj, ScalarizedObjective)
    for metric in obj.metrics:
        assert isinstance(metric, Metric)

    objectives = soo_config["optimization_options"]["scalarized_objective_options"]["objectives"]
    for objective, weight in zip(objectives, obj.weights):
        assert weight == objective["weight"]
