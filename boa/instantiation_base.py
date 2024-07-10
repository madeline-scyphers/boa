from __future__ import annotations

from ax import Objective as AxObjective
from ax.core.objective import ScalarizedObjective
from ax.service.utils.instantiation import InstantiationBase

from boa.config import BOAMetric, BOAObjective
from boa.metrics.metrics import PassThroughMetric, get_metric_from_config
from boa.metrics.modular_metric import ModularMetric
from boa.wrappers.base_wrapper import BaseWrapper


class BoaInstantiationBase(InstantiationBase):
    @classmethod
    def make_optimization_config(
        cls,
        objective: BOAObjective,
        wrapper: BaseWrapper = None,
        status_quo_defined: bool = False,
        **kwargs,
    ):
        outcome_constraints = cls.make_outcome_constraints(objective.outcome_constraints, status_quo_defined)
        for constraint in outcome_constraints:
            if not isinstance(constraint.metric, ModularMetric) or not getattr(constraint.metric, "wrapper", None):
                constraint.metric = PassThroughMetric(
                    name=constraint.metric.name, lower_is_better=constraint.metric.lower_is_better, wrapper=wrapper
                )

        return cls.optimization_config_from_objectives(
            cls.make_objectives(objective, wrapper=wrapper, **kwargs),
            cls.make_objective_thresholds(objective.objective_thresholds, status_quo_defined),
            outcome_constraints,
        )

    @classmethod
    def get_metric_from_metric_config(cls, metric_conf: BOAMetric, **kwargs) -> ModularMetric:
        metric = get_metric_from_config(metric_conf, **kwargs)
        return metric

    @classmethod
    def get_metrics_from_obj_config(cls, objective: BOAObjective, info_only=False, **kwargs) -> list[ModularMetric]:
        """"""
        metrics = []
        for metric_conf in objective.metrics:
            tracker = metric_conf.info_only
            metric = cls.get_metric_from_metric_config(metric_conf, **kwargs)
            if info_only is None:  # get all metrics
                metrics.append(metric)
            elif info_only is True and tracker:  # only get tracking metrics
                metrics.append(metric)
            elif info_only is False and not tracker:  # only get not tracking metrics
                metrics.append(metric)
        return metrics

    @classmethod
    def make_objectives(cls, objective: BOAObjective, **kwargs) -> list[AxObjective]:

        metrics = cls.get_metrics_from_obj_config(objective, **kwargs)

        weights = [metric.weight for metric in metrics]
        kw = {}
        if any(weights):
            kw["weights"] = weights
            if objective.minimize is not None:
                kw["minimize"] = objective.minimize
            output_objectives = [ScalarizedObjective(metrics=metrics, **kw)]
        else:
            output_objectives = [AxObjective(metric=metric, minimize=metric.lower_is_better) for metric in metrics]
        return output_objectives
