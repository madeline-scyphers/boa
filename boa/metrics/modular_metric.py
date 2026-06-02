"""
########################
Modular Metric
########################

"""

from __future__ import annotations

import logging
import random
from functools import partial
from typing import Any, Callable, Mapping, Optional

import pandas as pd

from boa.ax_api import (
    FromBotorch,
    IMetric,
    TParameterization,
)
from boa.metaclasses import MetricRegister
from boa.utils import (
    extract_init_args,
    get_dictionary_from_callable,
    serialize_init_args,
)
from boa.wrappers.base_wrapper import BOATrialContext, BaseWrapper

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


class ModularMetric(IMetric, metaclass=MetricRegister):
    """
    A wrappable metric defined by a generic deterministic function with the
    ability to inject a wrapper for higher customizability.
    The metric function can have some known or unknown noise such that each
    evaluation may be different, they will be centered around a true value with
    some optional ``sem``

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
    check_for_nans
        If True, check for NaNs in the results of the metric and fail the trial if found.
        If nans are not dealt with in some way, they can cause the optimization to fail.
    """

    _metric_to_eval = None

    def __init__(
        self,
        metric_to_eval: Callable | str = None,
        metric_func_kwargs: Optional[dict] = None,
        param_names: list[str] = None,
        name: Optional[str] = None,
        wrapper: Optional[BaseWrapper] = None,
        properties: Optional[dict[str]] = None,
        weight: Optional[float] = None,
        noise_sd: Optional[float] = 0,
        check_for_nans: Optional[bool] = True,
        lower_is_better: Optional[bool] = True,
        **kwargs
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

        self.param_names = param_names or []
        self.wrapper = wrapper
        self._weight = weight
        self.noise_sd = noise_sd
        # self._lower_is_better = lower_is_better
        super().__init__(name=name)
        self.properties = properties or {}
        self._trial_data_cache = {}
        self.check_for_nans = check_for_nans

    @classmethod
    def is_available_while_running(cls) -> bool:
        return False

    @property
    def weight(self):
        return self._weight

    @property
    def lower_is_better(self):
        return self._lower_is_better

    @lower_is_better.setter
    def lower_is_better(self, value):
        self._lower_is_better = value

    def fetch(
        self,
        trial_index: int,
        trial_metadata: Mapping[str, Any],
    ) -> tuple[int, float | tuple[float, float]]:
        trial_metadata = trial_metadata or {}
        if trial_index in self._trial_data_cache:
            return self._trial_data_cache[trial_index]
        
        parameterization = trial_metadata.get("parameterization", {})
        progression = trial_metadata.get("progression", 0)
        trial = BOATrialContext(index=trial_index, parameters=parameterization, trial_metadata=trial_metadata)
        # raise Exception(f'parameterization: {parameterization}\n wrapper: {self.wrapper}')
        if self.wrapper:
            wrapper_data = self.wrapper._fetch_trial_data(
                parameters=parameterization,
                param_names=self.param_names,
                trial_index=trial_index,
                trial_metadata=trial_metadata,
                trial=trial,
                metric_name=self.name,
            )
        elif self.name in trial_metadata:
            wrapper_data = trial_metadata[self.name]
        else:
            wrapper_data = parameterization

        sem = self.noise_sd
        wrapper_data = wrapper_data if wrapper_data is not None else {}
        eval_kwargs = {}
        if isinstance(wrapper_data, tuple) and len(wrapper_data) == 2:
            progression = wrapper_data[0]
            args = wrapper_data[1]
            if isinstance(wrapper_data[1], tuple):
                mean = wrapper_data[1][0]
                sem = wrapper_data[1][1]
            else:
                mean = wrapper_data[1]

        elif wrapper_data is not None and not isinstance(wrapper_data, dict):
            wrapper_data = {"wrapper_args": wrapper_data}

        if self.check_for_nans and self._has_invalid_result(wrapper_data):
            raise ValueError(f"NaNs in Results for Trial {trial_index}, failing trial")

        if isinstance(wrapper_data, dict):
            eval_source = wrapper_data
            sem = eval_source.pop("sem", self.noise_sd)
            progression = eval_source.pop("progression", progression)
            args = eval_source.pop("wrapper_args", [])
            if args is None:
                args = []
            elif not isinstance(args, (list, tuple)):
                args = [args]
            eval_kwargs = get_dictionary_from_callable(self.metric_to_eval, eval_source)
    
        fetched = self.f(*args, **eval_kwargs)
        if self.check_for_nans and self._has_invalid_result(fetched):
            raise ValueError(f"NaNs in Results for Trial {trial_index}, failing trial")

        if isinstance(fetched, (int, float)):
            mean = fetched
        elif len(fetched) == 2:
            mean = float(fetched[0])
            sem = float([fetched[1]])
        elif fetched:
            mean = float(fetched[0])
        else:
            raise ValueError(f"Wrapper function did not return or metric eval did not return anything for trial index: {trial_index}")
        
        outcome = (float(mean), float(sem)) if sem is not None else float(mean)
        result = (int(progression), outcome)
        self._trial_data_cache[trial_index] = result
        return result

    def _evaluate(self, params: TParameterization, **kwargs) -> float:
        params = dict(params)
        kwargs.update(params.pop("kwargs", {}))
        args = kwargs.pop("wrapper_args", [])
        if not isinstance(args, (list, tuple)):
            args = [args]
        return self.f(*args, **get_dictionary_from_callable(self.metric_to_eval, kwargs))

    def f(self, *args, **kwargs):
        if self.metric_func_kwargs:  # always pass the metric_func_kwargs, don't fail silently
            kwargs.update(self.metric_func_kwargs)
        return self.metric_to_eval(*args, **kwargs)

    @staticmethod
    def _has_invalid_result(value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            return value.lower() in {"nan", "na"}
        if isinstance(value, Mapping):
            return any(ModularMetric._has_invalid_result(v) for v in value.values())
        if isinstance(value, (list, tuple, set)):
            return any(ModularMetric._has_invalid_result(v) for v in value)
        try:
            invalid = pd.isna(value)
        except TypeError:
            return False
        if isinstance(invalid, bool):
            return invalid
        if hasattr(invalid, "any"):
            return bool(invalid.any())
        return False

    def clone(self) -> "ModularMetric":
        """Create a copy of this Metric."""
        cls = type(self)
        return cls(
            **self.serialize_init_args(self),
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
        return serialize_init_args(
            class_=obj, match_private=True, exclude_fields=["wrapper"]
        )

    @classmethod
    def deserialize_init_args(
        cls, args: dict[str, Any], decoder_registry=None, class_decoder_registry=None
    ) -> dict[str, Any]:
        """Given a dictionary, deserialize the properties needed to initialize the
        object. Used for storage.
        """
        return extract_init_args(
            args=args, class_=cls, match_private=True, exclude_fields=["wrapper"]
        )
