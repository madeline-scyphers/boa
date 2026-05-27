from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Any

from boa.ax_api import (
    ChoiceParameterConfig,
    DerivedParameterConfig,
    MultiObjective,
    RangeParameterConfig,
    choose_generation_strategy_new,
    optimization_config_from_string,
)
from boa.scheduler import BOAClient
from boa.config import BOAConfig, BOAMetric, MetricType
from boa.metrics.metrics import get_metric_from_config
from boa.runner import WrappedJobRunner
from boa.wrappers.base_wrapper import BaseWrapper
from boa.scheduler import BOAClient

PARAMETER_CONFIGS = {
    "choice": ChoiceParameterConfig,
    "range": RangeParameterConfig,
    "derived": DerivedParameterConfig,
}


def _parameter_config_from_dict(parameter: dict[str, Any]):
    parameter = copy.deepcopy(parameter)
    parameter_type = parameter.pop("type")
    if parameter_type == "fixed":
        parameter["values"] = [parameter.pop("value")]
        parameter.setdefault("is_ordered", False)
        return ChoiceParameterConfig(**parameter)
    if parameter_type == "range" and isinstance(parameter.get("bounds"), list):
        parameter["bounds"] = tuple(parameter["bounds"])
    return PARAMETER_CONFIGS[parameter_type](**parameter)


def _metric_names_from_optimization(config: BOAConfig) -> list[str]:
    opt_config = optimization_config_from_string(
        objective_str=config.optimization.objective,
        outcome_constraint_strs=config.optimization.outcome_constraints,
    )
    metric_names = []
    if isinstance(opt_config.objective, MultiObjective):
        for objective in opt_config.objective.objectives:
            metric_names.extend(objective.metric_names)
    else:
        metric_names.extend(opt_config.objective.metric_names)
    metric_names.extend(config.optimization.tracking_metrics)
    for constraint in opt_config.outcome_constraints:
        metric_names.extend(constraint.metric_names)
    return list(dict.fromkeys(metric_names))


def _configure_generation_strategy(client: BOAClient, config: BOAConfig) -> None:
    if config.generation_strategy is None:
        return
    generation_strategy = config.generation_strategy
    if generation_strategy.struct.method == "custom":
        client.set_generation_strategy(
            generation_strategy=choose_generation_strategy_new(
                struct=generation_strategy.struct,
                model_config=generation_strategy.model_config,
                botorch_acqf_class=generation_strategy.botorch_acqf_class,
            )
        )
        return
    client.configure_generation_strategy(**asdict(generation_strategy.struct))


def get_client(config: BOAConfig, wrapper: BaseWrapper | None = None, runner=None, **kwargs) -> BOAClient:
    """Instantiate and configure BOA's Ax >= 1 Client from a BOAConfig."""

    client = BOAClient(wrapper=wrapper, orchestrator_options=config.orchestrator, **kwargs)
    parameters = [_parameter_config_from_dict(parameter) for parameter in config.parameters]
    client.configure_experiment(
        parameters=parameters,
        parameter_constraints=config.parameter_constraints,
        name=config.script_options.exp_name,
    )
    client.configure_optimization(
        objective=config.optimization.objective,
        outcome_constraints=config.optimization.outcome_constraints,
        pruning_target_parameterization=config.optimization.pruning_target_parameterization,
    )
    _configure_generation_strategy(client=client, config=config)

    if runner is None:
        runner = WrappedJobRunner(wrapper=wrapper)
    client.configure_runner(runner=runner)

    if config.optimization.tracking_metrics:
        client.configure_tracking_metrics(metric_names=config.optimization.tracking_metrics)

    metrics = []
    for name in _metric_names_from_optimization(config):
        metric_conf = config.optimization.metrics.get(name)
        if metric_conf is None:
            metric_conf = BOAMetric(metric=name, metric_type=MetricType.PASSTHROUGH)
        metrics.append(get_metric_from_config(config=metric_conf, wrapper=wrapper))
    if metrics:
        client.configure_metrics(metrics=metrics)
    return client