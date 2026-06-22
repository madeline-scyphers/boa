from boa.ax_api import (
    Metric,
    MultiObjective,
    MultiObjectiveOptimizationConfig,
    Objective,
    OptimizationConfig,
    OutcomeConstraint,
    ScalarizedObjective,
    optimization_config_from_string,
)


def test_soo_config_loading(soo_config):
    optimization_config = optimization_config_from_string(
        objective_str=soo_config.optimization.objective,
        outcome_constraint_strs=soo_config.optimization.outcome_constraints,
    )
    assert isinstance(optimization_config, OptimizationConfig)

    outcome_constraints = optimization_config.outcome_constraints
    for outcome_constraint in outcome_constraints:
        assert isinstance(outcome_constraint, OutcomeConstraint)

    obj = optimization_config.objective
    assert isinstance(obj, ScalarizedObjective)
    for metric in obj.metrics:
        assert isinstance(metric, Metric)

    assert obj.weights == [-1.0, -2.0]


def test_moo_config_loading(moo_config):
    optimization_config = optimization_config_from_string(
        objective_str=moo_config.optimization.objective,
        outcome_constraint_strs=moo_config.optimization.outcome_constraints,
    )
    assert isinstance(optimization_config, MultiObjectiveOptimizationConfig)

    outcome_constraints = optimization_config.outcome_constraints
    for outcome_constraint in outcome_constraints:
        assert isinstance(outcome_constraint, OutcomeConstraint)

    obj = optimization_config.objective
    assert isinstance(obj, MultiObjective)
    for objective in obj.objectives:
        assert isinstance(objective, Objective)
