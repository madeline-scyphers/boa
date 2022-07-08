from __future__ import annotations

from ax import Objective
from ax.core.objective import ScalarizedObjective
from ax.service.utils.instantiation import (
    InstantiationBase,
    MetricObjective,
    ObjectiveProperties,
)

from boa.metrics.metrics import get_metric_from_config


class BoaInstantiationBase(InstantiationBase):
    @classmethod
    def make_optimization_config(
        cls,
        objectives: dict,
        objective_thresholds: list[str] = None,
        outcome_constraints: list[str] = None,
        status_quo_defined: bool = False,
        weights: list[float] | None = None,
        minimize: bool = None,
        **kwargs,
    ):
        objective_thresholds = objective_thresholds or []
        outcome_constraints = outcome_constraints or []
        return cls.optimization_config_from_objectives(
            cls.make_objectives(objectives, weights=weights, minimize=minimize, **kwargs),
            cls.make_objective_thresholds(objective_thresholds, status_quo_defined),
            cls.make_outcome_constraints(outcome_constraints, status_quo_defined),
        )

    @classmethod
    def get_metric_from_obj_config(cls, metric_opts, **kwargs):
        if metric_opts.get("minimize"):
            kwargs["lower_is_better"] = metric_opts["minimize"]
        metric = get_metric_from_config(metric_opts, **kwargs)
        return metric

    @classmethod
    def get_metrics_from_obj_config(cls, objectives, **kwargs):
        metrics = []
        for metric_opts in objectives:
            metric = cls.get_metric_from_obj_config(metric_opts, **kwargs)
            metrics.append(metric)
        return metrics

    @classmethod
    def make_objectives(
        cls, objectives: dict, weights: list[float] | None = None, minimize: bool = None, **kwargs
    ) -> list[Objective]:
        metrics = cls.get_metrics_from_obj_config(objectives, **kwargs)

        kw = {}
        if weights:
            kw["weights"] = weights
            if minimize:
                kw["minimize"] = minimize
            output_objectives = [ScalarizedObjective(metrics=metrics, **kw)]
        else:
            output_objectives = [
                Objective(metric=metric, minimize=metric.lower_is_better) for metric in metrics
            ]
        return output_objectives
