"""
Metrics

Built-in metrics:

- MSE, MeanSquaredError
- RMSE, RootMeanSquaredError
- R2, RSquared
"""

from __future__ import annotations

import logging
from functools import partial
from inspect import isclass
from typing import Callable, Optional

import ax.utils.measurement.synthetic_functions
import botorch.test_functions.synthetic
import numpy as np
import pandas as pd
import sklearn.metrics
from ax import Metric
from ax.core.base_trial import BaseTrial
from ax.core.data import Data
from ax.core.types import TParameterization
from ax.metrics.noisy_function import NoisyFunctionMetric
from ax.utils.measurement.synthetic_functions import FromBotorch, from_botorch

import boa.metrics.synthethic_funcs
from boa.metaclasses import MetricRegister, MetricToEvalRegister
from boa.metrics.metric_funcs import metric_from_json, metric_from_yaml
from boa.metrics.metric_funcs import (
    normalized_root_mean_squared_error as normalized_root_mean_squared_error_,
)
from boa.utils import get_dictionary_from_callable, serialize_init_args
from boa.wrapper import BaseWrapper

logger = logging.getLogger(__name__)


def get_metric_from_config(config, instantiate=True, **kwargs):
    if config.get("metric"):
        config = config["metric"]
    if config.get("boa_metric"):
        kwargs["metric_name"] = config["boa_metric"]
        metric = get_metric_by_class_name(instantiate=instantiate, **config, **kwargs)
    elif config.get("sklearn_metric"):
        kwargs["metric_name"] = config["sklearn_metric"]
        kwargs["sklearn_"] = True
        metric = get_metric_by_class_name(instantiate=instantiate, **config, **kwargs)
    elif config.get("synthetic_metric"):
        metric = setup_synthetic_metric(instantiate=instantiate, **config, **kwargs)
    else:
        # TODO link to docs for configuration when it exists
        raise KeyError("No valid configuration for metric found.")
    return metric


def get_metric_by_class_name(metric_name, instantiate=True, sklearn_=False, **kwargs):
    if sklearn_:
        return setup_sklearn_metric(metric_name, instantiate=True, **kwargs)
    return globals()[metric_name](**kwargs) if instantiate else globals()[metric_name]


def get_sklearn_func(metric_to_eval):
    if metric_to_eval in sklearn.metrics.__all__:
        metric = getattr(sklearn.metrics, metric_to_eval)
    else:
        raise AttributeError(f"Sklearn metric: {metric_to_eval} not found!")
    return metric


def setup_sklearn_metric(metric_to_eval, instantiate=True, **kw):
    metric = get_sklearn_func(metric_to_eval)

    def modular_sklearn_metric(**kwargs):
        return ModularMetric(**{**kw, **kwargs, "metric_to_eval": metric})

    return modular_sklearn_metric(**kw) if instantiate else modular_sklearn_metric


def get_synth_func(synthetic_metric):
    synthetic_funcs_modules = [
        boa.metrics.synthethic_funcs,
        ax.utils.measurement.synthetic_functions,
        botorch.test_functions.synthetic,
    ]
    for module in synthetic_funcs_modules:
        try:
            return getattr(module, synthetic_metric)
        except AttributeError:
            continue
    # If we don't find the class by the end of the modules, raise attribute error
    raise AttributeError(
        f"boa synthetic function: {synthetic_metric}"
        f" not found in modules: {synthetic_funcs_modules}!"
    )


def setup_synthetic_metric(synthetic_metric, instantiate=True, **kw):
    metric = get_synth_func(synthetic_metric)

    if isclass(metric) and issubclass(metric, ax.utils.measurement.synthetic_functions):
        metric = metric()  # if they pass a ax synthetic metric class, not instance
    elif isclass(metric) and issubclass(
        metric, botorch.test_functions.synthetic.SyntheticTestFunction
    ):
        # botorch synthetic functions need to be converted
        metric = from_botorch(botorch_synthetic_function=metric())

    def modular_synthetic_metric(**kwargs):
        return ModularMetric(**{**kw, **kwargs, "metric_to_eval": metric})

    return modular_synthetic_metric(**kw) if instantiate else modular_synthetic_metric


def _get_name(obj):
    if hasattr(obj, "__name__"):
        return obj.__name__
    elif isinstance(obj, FromBotorch):
        # Using metrics that are FromBotorch(botorch synthetic_funcs) leaves us
        # with having to rely on a private attribute to get to the funcs __name__
        # watch for breaking someday
        obj = obj._botorch_function
    elif isinstance(obj, partial):
        obj = obj.func
    else:
        obj = obj.__class__
    return _get_name(obj)


class MetricToEval(metaclass=MetricToEvalRegister):
    def __init__(
        self, *, func: Callable | str, func_kwargs: Optional[dict] = None, type_: str = None
    ):
        if isinstance(func, str):
            func = self.func_from_str(func, type_)
        self.func = func
        self.func_kwargs = func_kwargs or {}
        self.name = _get_name(func)
        self.type_ = type_

    def __call__(self, *args, **kwargs):
        return self.func(
            *args, **get_dictionary_from_callable(self.func, {**self.func_kwargs, **kwargs})
        )

    def to_dict(self):
        return {
            "__type": self.__class__.__name__,
            "func": self.name,
            "func_kwargs": self.func_kwargs,
            "type_": self.type_,
        }

    @classmethod
    def func_from_str(cls, name: str, type_: str = None):
        if type_ == "sklearn_metric":
            func = get_sklearn_func(name)
        elif type_ == "synthetic_metric":
            func = get_synth_func(name)
        elif type_ == "boa_metric" or type_ is None:
            func = globals()[name]
            try:
                func = func()
            except Exception as e:
                logger.debug(
                    "func: %s not callable because of: %r", getattr(func, "__name__", func), e
                )
            if isinstance(func, ModularMetric):
                func = func.metric_to_eval.func
            elif isinstance(func, MetricToEval):
                func = func.func
            # else func is just func
        else:
            raise ValueError(f"{cls.__name__} type_: {type_} invalid!")
        return func


class ModularMetric(NoisyFunctionMetric, metaclass=MetricRegister):
    def __init__(
        self,
        metric_to_eval: Callable,
        param_names: list[str] = None,
        noise_sd: Optional[float] = 0.0,
        metric_func_kwargs: Optional[dict] = None,
        wrapper: Optional[BaseWrapper] = None,
        properties: Optional[dict[str]] = None,
        type_: Optional[str] = None,
        **kwargs,
    ):

        if kwargs.get("name") is None:
            kwargs["name"] = _get_name(metric_to_eval)
        param_names = param_names if param_names is not None else []
        self.metric_func_kwargs = metric_func_kwargs or {}
        self.metric_to_eval = MetricToEval(
            func=metric_to_eval, func_kwargs=metric_func_kwargs, type_=type_
        )
        self.wrapper = wrapper or BaseWrapper()
        super().__init__(
            param_names=param_names,
            noise_sd=noise_sd,
            **get_dictionary_from_callable(NoisyFunctionMetric.__init__, kwargs),
        )
        self.properties = properties or {}

    @classmethod
    def is_available_while_running(cls) -> bool:
        return False

    def fetch_trial_data(self, trial: BaseTrial, *args, **kwargs):
        wrapper_kwargs = (
            self.wrapper.fetch_trial_data(
                trial=trial,
                metric_properties=self.properties,
                metric_name=self.name,
                *args,
                **kwargs,
            )
            if self.wrapper
            else {}
        )
        wrapper_kwargs = wrapper_kwargs or {}
        safe_kwargs = {"trial": trial, **kwargs, **wrapper_kwargs}
        if isinstance(self.metric_to_eval.func, Metric):
            return self.metric_to_eval.func.fetch_trial_data(
                *args,
                **get_dictionary_from_callable(
                    self.metric_to_eval.func.fetch_trial_data, safe_kwargs
                ),
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
        kwargs["x"] = np.array([params[p] for p in self.param_names if p in params])
        return self.f(**get_dictionary_from_callable(self.metric_to_eval, kwargs))

    def f(self, *args, **kwargs):
        return self.metric_to_eval(*args, **kwargs)

    def clone(self) -> "Metric":
        """Create a copy of this Metric."""
        cls = type(self)
        return cls(
            **serialize_init_args(self, parents=[NoisyFunctionMetric], match_private=True),
        )

    def to_dict(self) -> dict:
        """Convert Ax experiment to a dictionary."""
        parents = self.__class__.mro()[1:]  # index 0 is the class itself

        # We don't want to match init args for Metric class and back, because
        # NoisyFunctionMetric changes the init parameters22
        try:
            index_of_metric = parents.index(Metric)
        except ValueError:
            index_of_metric = None
        p_b4_metric = parents[:index_of_metric]

        wrapper_state = serialize_init_args(
            self, parents=p_b4_metric, match_private=True, exclude_fields=["wrapper"]
        )

        # wrapper_state = convert_type(wrapper_state, {Path: str})
        return {"__type": self.__class__.__name__, **wrapper_state}

    def __repr__(self) -> str:
        init_dict = serialize_init_args(self, parents=[NoisyFunctionMetric], match_private=True)
        init_dict = {k: v for k, v in init_dict.items() if v}

        if isinstance(init_dict["metric_to_eval"], partial):
            init_dict["metric_to_eval"] = init_dict["metric_to_eval"].func

        arg_str = " ".join(f"{k}={v}" for k, v in init_dict.items())
        return f"{self.__class__.__name__}({arg_str})"


MSE = setup_sklearn_metric("mean_squared_error", lower_is_better=True, instantiate=False)
MeanSquaredError = MSE
mean_squared_error = MSE

RMSE = setup_sklearn_metric(
    "mean_squared_error",
    name="root_mean_squared_error",
    lower_is_better=True,
    metric_func_kwargs={"squared": False},
    instantiate=False,
)
RootMeanSquaredError = RMSE
root_mean_squared_error = RMSE

R2 = setup_sklearn_metric("r2_score", instantiate=False)
RSquared = R2
Mean = partial(ModularMetric, metric_to_eval=np.mean, lower_is_better=True)

MetricFromJSON = partial(ModularMetric, metric_to_eval=metric_from_json)
MetricFromYAML = partial(ModularMetric, metric_to_eval=metric_from_yaml)

NRMSE = partial(
    ModularMetric, metric_to_eval=normalized_root_mean_squared_error_, lower_is_better=True
)
NormalizedRootMeanSquaredError = NRMSE
normalized_root_mean_squared_error = NRMSE
