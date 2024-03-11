"""
########################
Modular Metric
########################

"""

from __future__ import annotations

import logging
from functools import partial
from typing import Any, Callable, Optional

import pandas as pd
from ax import Data, Metric, Trial
from ax.core.types import TParameterization
from ax.metrics.noisy_function import NoisyFunctionMetric
from ax.utils.common.result import Err, Ok
from ax.utils.measurement.synthetic_functions import FromBotorch

from boa.metaclasses import MetricRegister
from boa.utils import (
    extract_init_args,
    get_dictionary_from_callable,
    serialize_init_args,
)
from boa.wrappers.base_wrapper import BaseWrapper

logger = logging.getLogger(__file__)


def _get_func_by_name(metric: str):
    import boa.metrics.metric_funcs
    import boa.metrics.synthetic_funcs

    for func in [boa.metrics.metric_funcs.get_sklearn_func, boa.metrics.synthetic_funcs.get_synth_func]:
        try:
            return func(metric)
        except AttributeError:
            continue
    try:
        import boa.metrics.metrics

        M = boa.metrics.metrics.get_boa_metric(metric)
        metric_to_eval = M._metric_to_eval  # class defined default for deserialization
        if not metric_to_eval:  # not defined on class level
            m = M()
            metric_to_eval = m.metric_to_eval
        return metric_to_eval
    except (AttributeError, TypeError):
        raise AttributeError(f"No metric with name {metric} found!")


def _get_name(obj):
    if isinstance(obj, str):
        return obj
    elif hasattr(obj, "__name__"):
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


class ModularMetric(NoisyFunctionMetric, metaclass=MetricRegister):
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
    :class:`Wrapper<.BaseWrapper>`, which has will run methods
    such as  :meth:`.BaseWrapper.fetch_trial_data` before
    calling the specified metric to evaluate, which can allow you
    to preprocess/prepare model output data for your metric calculation.


    Parameters
    ----------
    metric_to_eval
    metric_func_kwargs
        dictionary of keyword arguments to pass to the metric to eval function
    noise_sd
        Scale of normal noise added to the function result. If None, interpret the function as
        noisy with unknown noise level.
    param_names
        A list of names of parameters to be passed to your wrapper.
        Useful for filtering out parameters before those parameters are passed to
        your metric
    name
        The name of the metric, if not specified, defaults to name of ``metric_to_eval``
    wrapper
        Boa wrapper to handle running the model and getting the data, allows injecting custom
        function in the middle of ``ModularMetric``
    properties
        Arbitrary dictionary of properties to store. Properties need to be json
        serializable
    kwargs
    """

    _metric_to_eval = None

    def __init__(
        self,
        metric_to_eval: Callable | str = None,
        metric_func_kwargs: Optional[dict] = None,
        param_names: list[str] = None,
        noise_sd: Optional[float] = 0.0,
        name: Optional[str] = None,
        wrapper: Optional[BaseWrapper] = None,
        properties: Optional[dict[str]] = None,
        weight: Optional[float] = None,
        **kwargs,
    ):
        """"""  # remove init docstring from parent class to stop it showing in sphinx
        # some classes put their metric_to_evals as class attributes to access non instantiated for deserialization
        # also, if we don't access through __class__, it bounds it to self and passes self as first arg
        metric_to_eval = self.__class__._metric_to_eval or metric_to_eval
        if not metric_to_eval:
            raise TypeError("__init__() missing 1 required positional argument: 'metric_to_eval'")
        if "to_eval_name" in kwargs:
            self._to_eval_name = kwargs.pop("to_eval_name")
        else:
            self._to_eval_name = _get_name(metric_to_eval)
        self.metric_func_kwargs = metric_func_kwargs or {}
        if isinstance(metric_to_eval, str):
            metric_to_eval = _get_func_by_name(metric_to_eval)
        self.metric_to_eval = metric_to_eval

        if name is None:
            name = self._to_eval_name

        kwargs["param_names"] = param_names or []
        self.wrapper = wrapper or BaseWrapper()
        self._weight = weight
        super().__init__(
            noise_sd=noise_sd,
            name=name,
            **get_dictionary_from_callable(NoisyFunctionMetric.__init__, kwargs),
        )
        self.properties = properties or {}
        self._trial_data_cache = {}

    @classmethod
    def is_available_while_running(cls) -> bool:
        return False

    @property
    def weight(self):
        return self._weight

    def fetch_trial_data(self, trial: Trial, **kwargs):
        if trial.index in self._trial_data_cache:
            return Ok(Data(df=pd.DataFrame(self._trial_data_cache[trial.index])))
        wrapper_kwargs = (
            self.wrapper._fetch_trial_data(
                parameters=trial.arm.parameters,
                param_names=self.param_names,
                trial=trial,
                metric_name=self.name,
                **kwargs,
            )
            if self.wrapper
            else {}
        )
        if isinstance(wrapper_kwargs, dict):
            nan_checks = list(wrapper_kwargs.values())
        elif isinstance(wrapper_kwargs, list):
            nan_checks = wrapper_kwargs
        else:
            nan_checks = [wrapper_kwargs]
        for elem in nan_checks:
            if (
                (isinstance(elem, str) and ("nan" == elem.lower() or "na" == elem.lower()))
                or (isinstance(elem, float) and pd.isna(elem))
                or (elem is None)
            ):
                return Err(f"NaNs in Results for Trial {trial.index}, failing trial")

        wrapper_kwargs = wrapper_kwargs if wrapper_kwargs is not None else {}
        if wrapper_kwargs is not None and not isinstance(wrapper_kwargs, dict):
            wrapper_kwargs = {"wrapper_args": wrapper_kwargs}
        safe_kwargs = {"trial": trial, **kwargs, **wrapper_kwargs}
        trial = safe_kwargs.pop("trial")
        # We add our extra kwargs to the arm parameters so they can be passed to evaluate
        for arm in trial.arms_by_name.values():
            arm._parameters["kwargs"] = safe_kwargs
        try:
            if isinstance(self.metric_to_eval, Metric):
                trial_data = self.metric_to_eval.fetch_trial_data(
                    trial=trial,
                    **get_dictionary_from_callable(self.metric_to_eval.fetch_trial_data, safe_kwargs),
                )
            else:
                trial_data = super().fetch_trial_data(trial=trial, **safe_kwargs)
            if "sem" in safe_kwargs and not isinstance(trial_data, Err):
                trial_df = trial_data.unwrap().df
                trial_df["sem"] = safe_kwargs["sem"]
                trial_data = Ok(Data(df=trial_df))
            if not isinstance(trial_data, Err):
                self._trial_data_cache[trial.index] = trial_data.unwrap().df.to_dict(
                    orient="list"
                )  # the format ax uses to put them in
        finally:
            # We remove the extra parameters from the arms for json serialization
            [arm._parameters.pop("kwargs") for arm in trial.arms_by_name.values()]
        return trial_data

    def _evaluate(self, params: TParameterization, **kwargs) -> float:
        kwargs.update(params.pop("kwargs"))
        args = kwargs.pop("wrapper_args", [])
        return self.f(*args, **get_dictionary_from_callable(self.metric_to_eval, kwargs))

    def f(self, *args, **kwargs):
        if self.metric_func_kwargs:  # always pass the metric_func_kwargs, don't fail silently
            kwargs.update(self.metric_func_kwargs)
        return self.metric_to_eval(*args, **kwargs)

    def clone(self) -> "Metric":
        """Create a copy of this Metric."""
        cls = type(self)
        return cls(
            **serialize_init_args(self, parents=[NoisyFunctionMetric], match_private=True),
        )

    def to_dict(self) -> dict:
        """Convert the Metric to a dictionary."""

        init_args = self.serialize_init_args(self)
        init_args["metric_to_eval"] = self._to_eval_name
        return {"__type": self.__class__.__name__, **init_args}

    @classmethod
    def serialize_init_args(cls, obj: Any) -> dict[str, Any]:
        """Serialize the properties needed to initialize the object.
        Used for storage.
        """
        parents = cls.mro()[1:]  # index 0 is the class itself

        # We don't want to match init args for Metric class and back, because
        # NoisyFunctionMetric changes the init parameters and doesn't pass and take
        # arbitrary *args and **kwargs
        try:
            index_of_metric = parents.index(Metric)
        except ValueError:
            index_of_metric = None
        parents_b4_metric = parents[:index_of_metric]

        return serialize_init_args(
            class_=obj, parents=parents_b4_metric, match_private=True, exclude_fields=["wrapper"]
        )

    @classmethod
    def deserialize_init_args(
        cls, args: dict[str, Any], decoder_registry=None, class_decoder_registry=None
    ) -> dict[str, Any]:
        """Given a dictionary, deserialize the properties needed to initialize the
        object. Used for storage.
        """
        parents = cls.mro()[1:]  # index 0 is the class itself

        # We don't want to match init args for Metric class and back, because
        # NoisyFunctionMetric changes the init parameters and doesn't pass and take
        # arbitrary *args and **kwargs
        try:
            index_of_metric = parents.index(Metric)
        except ValueError:
            index_of_metric = None
        parents_b4_metric = parents[:index_of_metric]

        return extract_init_args(
            args=args, class_=cls, parents=parents_b4_metric, match_private=True, exclude_fields=["wrapper"]
        )
