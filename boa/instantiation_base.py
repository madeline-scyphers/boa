from __future__ import annotations

from ax import Objective as AxObjective
from ax.core.objective import ScalarizedObjective
from ax.service.utils.instantiation import InstantiationBase

from boa.config import Metric, Objective
from boa.metrics.metrics import get_metric_from_config
from boa.metrics.modular_metric import ModularMetric


class BoaInstantiationBase(InstantiationBase):
    @classmethod
    def make_optimization_config(
        cls,
        objective: Objective,
        status_quo_defined: bool = False,
        **kwargs,
    ):
        return cls.optimization_config_from_objectives(
            cls.make_objectives(objective, **kwargs),
            cls.make_objective_thresholds(objective.objective_thresholds, status_quo_defined),
            cls.make_outcome_constraints(objective.outcome_constraints, status_quo_defined),
        )

    @classmethod
    def get_metric_from_metric_config(cls, metric_conf: Metric, **kwargs) -> ModularMetric:
        metric = get_metric_from_config(metric_conf, **kwargs)
        return metric

    @classmethod
    def get_metrics_from_obj_config(cls, objective: Objective, info_only=False, **kwargs) -> list[ModularMetric]:
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
    def make_objectives(cls, objective: Objective, **kwargs) -> list[AxObjective]:

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
