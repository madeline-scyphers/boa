from ax import (
    Metric,
    MultiObjective,
    MultiObjectiveOptimizationConfig,
    Objective,
    OptimizationConfig,
    OutcomeConstraint,
)
from ax.core.objective import ScalarizedObjective

from boa import BoaInstantiationBase


def test_soo_config_loading(soo_config):
    optimization_config = BoaInstantiationBase.make_optimization_config(
        soo_config.objective,
    )
    assert isinstance(optimization_config, OptimizationConfig)

    outcome_constraints = optimization_config.outcome_constraints
    for outcome_constraint in outcome_constraints:
        assert isinstance(outcome_constraint, OutcomeConstraint)

    obj = optimization_config.objective
    assert isinstance(obj, ScalarizedObjective)
    for metric in obj.metrics:
        assert isinstance(metric, Metric)

    weights = [metric.weight for metric in soo_config.objective.metrics]

    for w1, w2 in zip(obj.weights, weights):
        assert w1 == w2


def test_moo_config_loading(moo_config):
    optimization_config = BoaInstantiationBase.make_optimization_config(
        moo_config.objective,
    )
    assert isinstance(optimization_config, MultiObjectiveOptimizationConfig)

    outcome_constraints = optimization_config.outcome_constraints
    for outcome_constraint in outcome_constraints:
        assert isinstance(outcome_constraint, OutcomeConstraint)

    obj = optimization_config.objective
    assert isinstance(obj, MultiObjective)
    for objective in obj.objectives:
        assert isinstance(objective, Objective)
