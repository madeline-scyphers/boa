from __future__ import annotations

import logging
from functools import partial
from inspect import isclass
from typing import Callable, Optional

import ax.utils.measurement.synthetic_functions
import botorch.test_functions.synthetic
import numpy as np
import sklearn.metrics
from ax import Metric
from ax.core.base_trial import BaseTrial
from ax.core.types import TParameterization
from ax.metrics.noisy_function import NoisyFunctionMetric
from ax.utils.measurement.synthetic_functions import FromBotorch, from_botorch

import boa.metrics.synthethic_funcs
from boa.metaclasses import MetricRegister, MetricToEvalRegister
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
    return get_boa_metric(metric_name)(**kwargs) if instantiate else get_boa_metric(metric_name)


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


def get_synth_func(synthetic_metric: str):
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
        f"boa synthetic function: {synthetic_metric}" f" not found in modules: {synthetic_funcs_modules}!"
    )


def setup_synthetic_metric(synthetic_metric, instantiate=True, **kw):
    metric = get_synth_func(synthetic_metric)

    if isclass(metric) and issubclass(metric, ax.utils.measurement.synthetic_functions):
        metric = metric()  # if they pass a ax synthetic metric class, not instance
    elif isclass(metric) and issubclass(metric, botorch.test_functions.synthetic.SyntheticTestFunction):
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
    def __init__(self, *, func: Callable | str, func_kwargs: Optional[dict] = None, metric_type: str = None):
        if isinstance(func, str):
            func = self.func_from_str(func, metric_type)
        self.func = func
        self.func_kwargs = func_kwargs or {}
        self.name = _get_name(func)
        self.metric_type = metric_type

    def __call__(self, *args, **kwargs):
        return self.func(*args, **get_dictionary_from_callable(self.func, {**self.func_kwargs, **kwargs}))

    def to_dict(self):
        return {
            "__type": self.__class__.__name__,
            "func": self.name,
            "func_kwargs": self.func_kwargs,
            "metric_type": self.metric_type,
        }

    # TODO make a better way to do a None option
    @classmethod
    def func_from_str(cls, name: str, metric_type: str = None):
        if metric_type == "sklearn_metric":
            func = get_sklearn_func(name)
        elif metric_type == "synthetic_metric":
            func = get_synth_func(name)
        elif metric_type == "boa_metric" or metric_type is None:
            func = get_boa_metric(name)
            if isinstance(func, ModularMetric):
                func = func.metric_to_eval.func
            elif isinstance(func, MetricToEval):
                func = func.func
        else:
            raise ValueError(f"{cls.__name__} metric_type: {metric_type} invalid!")
        return func


def generic_closure(close_around, instantiate=True, **kw):
    def modular_metric(**kwargs):
        return close_around(**{**kw, **kwargs})

    return modular_metric(**kw) if instantiate else modular_metric


class ModularMetric(NoisyFunctionMetric, metaclass=MetricRegister):
    def __init__(
        self,
        metric_to_eval: Callable,
        metric_func_kwargs: Optional[dict] = None,
        # param_names: list[str] = None,
        noise_sd: Optional[float] = 0.0,
        name: Optional[str] = None,
        wrapper: Optional[BaseWrapper] = None,
        properties: Optional[dict[str]] = None,
        metric_type: Optional[str] = None,
        **kwargs,
    ):
        """
        A wrappable metric defined by a generic deterministic function with the
        ability to inject a wrapper for higher customizability.
        The metric function can have some known or unknown noise such that each
        evaluation may be different, they will be centered around a true value with
        some ``noise_sd``

        The deterministic metric function to compute is implemented by passing
        some callable (a function or class with ``__call__``) to argument
        ``metric_to_eval``.

        You can further customize the behavior of your metric by passing a
        :class:`Wrapper<boa.wrapper.BaseWrapper>`, which has will run methods
        such as  :meth:`~boa.wrapper.BaseWrapper.fetch_trial_data` before
        calling the specified metric to evaluate, which can allow you
        to preprocess/prepare model output data for your metric calculation.


        Parameters
        ----------
        metric_to_eval : Callable
        metric_func_kwargs : Optional[dict]
            dictionary of keyword arguments to pass to the metric to eval function
        noise_sd : Optional[float]
            Scale of normal noise added to the function result. If None, interpret the function as
            noisy with unknown noise level.
        name : Optional[str]
            name: Name of the metric, if not specified, defaults to name of ``metric_to_eval``
        wrapper : Optional[BaseWrapper]
            Boa wrapper to handle running the model and getting the data, allows injecting custom
            function in the middle of ``ModularMetric``
        properties : Optional[dict[str]]
            Arbitrary dictionary of properties to store. Properties need to be json
            serializable
        kwargs
        """

        if name is None:
            name = _get_name(metric_to_eval)
        if "param_names" not in kwargs:
            kwargs["param_names"] = []
        # param_names = param_names if param_names is not None else []
        self.metric_func_kwargs = metric_func_kwargs or {}
        self.metric_to_eval = MetricToEval(func=metric_to_eval, func_kwargs=metric_func_kwargs, metric_type=metric_type)
        self.wrapper = wrapper or BaseWrapper()
        super().__init__(
            noise_sd=noise_sd,
            name=name,
            **get_dictionary_from_callable(NoisyFunctionMetric.__init__, kwargs),
        )
        self.properties = properties or {}

    @classmethod
    def is_available_while_running(cls) -> bool:
        return False

    def fetch_trial_data(self, trial: BaseTrial, **kwargs):
        wrapper_kwargs = (
            self.wrapper.fetch_trial_data(
                trial=trial,
                metric_properties=self.properties,
                metric_name=self.name,
                **kwargs,
            )
            if self.wrapper
            else {}
        )
        wrapper_kwargs = wrapper_kwargs or {}
        safe_kwargs = {"trial": trial, **kwargs, **wrapper_kwargs}
        trial = safe_kwargs.pop("trial")
        # We add our extra kwargs to the arm parameters so they can be passed to evaluate
        for arm in trial.arms_by_name.values():
            arm._parameters["kwargs"] = safe_kwargs
        try:
            if isinstance(self.metric_to_eval.func, Metric):
                trial_data = self.metric_to_eval.func.fetch_trial_data(
                    trial=trial,
                    **get_dictionary_from_callable(self.metric_to_eval.func.fetch_trial_data, safe_kwargs),
                )
            else:
                trial_data = super().fetch_trial_data(trial=trial, **safe_kwargs)
        finally:
            # We remove the extra parameters from the arms for json serialization
            [arm._parameters.pop("kwargs") for arm in trial.arms_by_name.values()]
        return trial_data

    def _evaluate(self, params: TParameterization, **kwargs) -> float:
        kwargs.update(params.pop("kwargs"))
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

        wrapper_state = serialize_init_args(self, parents=p_b4_metric, match_private=True, exclude_fields=["wrapper"])

        # wrapper_state = convert_type(wrapper_state, {Path: str})
        return {"__type": self.__class__.__name__, **wrapper_state}

    def __repr__(self) -> str:
        init_dict = serialize_init_args(self, parents=[NoisyFunctionMetric], match_private=True)
        init_dict = {k: v for k, v in init_dict.items() if v}

        if isinstance(init_dict["metric_to_eval"], partial):
            init_dict["metric_to_eval"] = init_dict["metric_to_eval"].func

        arg_str = " ".join(f"{k}={v}" for k, v in init_dict.items())
        return f"{self.__class__.__name__}({arg_str})"


class METRICS:
    MSE = setup_sklearn_metric("mean_squared_error", lower_is_better=True, instantiate=False)
    MSE.__doc__ = """
    Mean squared error regression loss. Read more from sklearn mean squared error
    """

    MeanSquaredError = MSE
    mean_squared_error = MSE

    RMSE = setup_sklearn_metric(
        "mean_squared_error",
        name="root_mean_squared_error",
        lower_is_better=True,
        metric_func_kwargs={"squared": False},
        instantiate=False,
    )
    RMSE.__doc__ = """
    Root mean squared error regression loss. Read more from sklearn mean squared error with squared=False
    """
    RootMeanSquaredError = RMSE
    root_mean_squared_error = RMSE

    R2 = setup_sklearn_metric("r2_score", instantiate=False, lower_is_better=False)
    R2.__doc__ = """
    :math:`R^2` (coefficient of determination) regression score function.

    Best possible score is 1.0 and it can be negative (because the
    model can be arbitrarily worse). In the general case when the true y is
    non-constant, a constant model that always predicts the average y
    disregarding the input features would get a :math:`R^2` score of 0.0.
    """
    RSquared = R2

    Mean = generic_closure(close_around=ModularMetric, metric_to_eval=np.mean, lower_is_better=True, instantiate=False)
    Mean.__doc__ = """
    Arithmetic mean along the specified axis for your metric,
    Defaults to minimizization, if you want to maximize,
    specify lower_is_better: False or minimize: False in your configuration
    """
    NRMSE = generic_closure(
        close_around=ModularMetric,
        metric_to_eval=normalized_root_mean_squared_error_,
        lower_is_better=True,
        instantiate=False,
    )
    NRMSE.__doc__ = """
    Normalized root mean squared error. Like a normalized version of RMSE.
    Normalization defaults to IQR (inner quartile range).
    """
    NormalizedRootMeanSquaredError = NRMSE
    normalized_root_mean_squared_error = NRMSE


def get_boa_metric(name):
    return getattr(METRICS, name)
