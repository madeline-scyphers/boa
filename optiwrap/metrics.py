from __future__ import annotations

from functools import partial
from typing import Callable, Optional

import numpy as np
import pandas as pd
from ax import Data, Metric
from ax.core.base_trial import BaseTrial
from ax.core.data import Data
from ax.core.types import TParameterization
import sklearn.metrics

from optiwrap.utils import get_dictionary_from_callable, serialize_init_args
from optiwrap.wrapper import BaseWrapper


def get_metric_by_class_name(metric_cls_name):
    return globals()[metric_cls_name]


class ModularMetric(Metric):
    def __init__(
        self,
        metric_to_eval: Callable,
        param_names: list[str] = None,
        noise_sd: Optional[float] = 0.0,
        metric_func_kwargs: Optional[dict] = None,
        wrapper: Optional[BaseWrapper] = None,
        **kwargs
    ):
        self.param_names = param_names if param_names is not None else []
        self.noise_sd = noise_sd
        self.metric_func_kwargs = metric_func_kwargs or {}
        self.metric_to_eval = partial(metric_to_eval, **self.metric_func_kwargs)
        self.wrapper = wrapper
        super().__init__(**kwargs)

    @classmethod
    def is_available_while_running(cls) -> bool:
        return True

    def fetch_trial_data(self, trial: BaseTrial, *args, **kwargs):
        wrapper_kwargs = (
            self.wrapper.fetch_trial_data(trial=trial, *args, **kwargs) if self.wrapper else {}
        )
        wrapper_kwargs = wrapper_kwargs or {}
        safe_kwargs = {"trial": trial, **kwargs, **wrapper_kwargs}
        if isinstance(self.metric_to_eval, Metric):
            return self.metric_to_eval.fetch_trial_data(
                *args,
                **get_dictionary_from_callable(self.metric_to_eval.fetch_trial_data, safe_kwargs),
            )
        else:
            return self._fetch_trial_data_of_func(*args, **safe_kwargs)

    def _fetch_trial_data_of_func(self, trial: BaseTrial, noisy: bool = True, **kwargs) -> Data:
        noise_sd = self.noise_sd if noisy else 0.0
        arm_names = []
        mean = []
        for name, arm in trial.arms_by_name.items():
            arm_names.append(name)
            val = self._evaluate(params=arm.parameters, **kwargs)
            if noise_sd:
                val = val + noise_sd * np.random.randn()
            mean.append(val)
        # indicate unknown noise level in data
        if noise_sd is None:
            noise_sd = float("nan")
        df = pd.DataFrame(
            {
                "arm_name": arm_names,
                "metric_name": self.name,
                "mean": mean,
                "sem": noise_sd,
                "trial_index": trial.index,
            }
        )
        return Data(df=df)

    def _evaluate(self, params: TParameterization, **kwargs) -> float:
        kwargs["x"] = np.array([params[p] for p in self.param_names])
        return self.metric_to_eval(**get_dictionary_from_callable(self.metric_to_eval, kwargs))

    def clone(self) -> "Metric":
        """Create a copy of this Metric."""
        cls = type(self)
        return cls(
            **serialize_init_args(
                self, parents=[Metric], match_private=True
            ),
        )


def setup_SklearnMetric(metric_to_eval, **kw):
    if metric_to_eval in sklearn.metrics.__all__:
        metric = getattr(sklearn.metrics, metric_to_eval)
    else:
        raise ValueError(f"Sklearn metric: {metric_to_eval} not found!")

    class SklearnMetric(ModularMetric):
        def __init__(self, *args, **kwargs):
            k = {**kw, **kwargs}  # we make sure to expand kw first to let them be overridden on instantiation
            super().__init__(metric_to_eval=metric, *args, **k)

    return SklearnMetric


MSE = setup_SklearnMetric("mean_squared_error")
MeanSquaredError = MSE
R2 = setup_SklearnMetric("r2_score")
RSquared = R2
