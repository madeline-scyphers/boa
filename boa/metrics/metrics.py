"""
########################
List of Metrics
########################

Metrics that are already defined in BOA:

- :class:`.PassThrough`
- :class:`.MeanSquaredError`
- :class:`.RootMeanSquaredError`
- :class:`.RSquared`
- :class:`.Mean`
- :class:`.NormalizedRootMeanSquaredError`

Any of these Metrics can be used directly in your configuration file.

Examples
========
..  code-block:: YAML

    # Single objective optimization config
    optimization_options:
        objective_options:
            objectives:
                # List all of your metrics here,
                # only list 1 metric for a single objective optimization
                - metric: RootMeanSquaredError

..  code-block:: YAML

    # MultiObjective Optimization config
    optimization_options:
        objective_options:
            objectives:
                # List all of your metrics here,
                # only list multiple objectives for a multi objective optimization
                - metric: RMSE
                - metric: R2

PassThrough Metric
******************

If your metric is computed elsewhere (say by your model code or your model wrapping code),
then you can use the PassThrough metric. PassThrough metric defaults to minimizing.
To mark as maximize, use ``minimize: False``.

..  code-block:: YAML

    # Single objective optimization config
    optimization_options:
        objective_options:
            objectives:
                # List all of your metrics here,
                # only list 1 metric for a single objective optimization
                - metric: PassThrough
                  name: foo  # optional, any name will work
                  minimize: False

You could also simply specify a name, with no metric type and it will
default to a pass through metric:

..  code-block:: YAML

    # Single objective optimization config
    optimization_options:
        objective_options:
            objectives:
                # List all of your metrics here,
                # only list 1 metric for a single objective optimization
                - name: foo  # optional, any name will work

If working in a language agnostic way, you can write out your output.json file like this
(see more at :mod:`Wrappers <boa.wrappers>`):

..  code-block:: JSON

    {
        "foo": 42
    }

If working with the Python API, your `fetch_trial_status` function could be
something like this

..  code-block:: python

    def fetch_trial_data(self, trial, *args, **kwargs):
        value = get_value_somehow()
        return value

"""
from __future__ import annotations

from typing import Iterable, Type

import numpy as np

from boa.metrics.metric_funcs import get_sklearn_func
from boa.metrics.metric_funcs import (
    normalized_root_mean_squared_error as normalized_root_mean_squared_error_,
)
from boa.metrics.metric_funcs import setup_sklearn_metric
from boa.metrics.modular_metric import ModularMetric
from boa.metrics.synthetic_funcs import setup_synthetic_metric


class PassThrough(ModularMetric):
    """
    Metric that just passes the value it receives back through,
    for example:

        {metric: 5}

    will just return 5.

    Defaults to minimizing, set `minimize: False` in your config if you wish
    to maximize.
    """

    _metric_to_eval = lambda x: x  # noqa: E731

    def _evaluate(self, params, **kwargs) -> float:
        kwargs.update(params.pop("kwargs"))
        args = kwargs["wrapper_args"]
        if not isinstance(args, Iterable):
            args = [args]
        if len(args) > 1:
            raise ValueError(
                "Pass Through Metric can only pass through one value.\n"
                "Check if you are passing more than one value to your pass through metric."
            )
        return self.f(*args)


PassThroughMetric = PassThrough
pass_through = PassThroughMetric
passthrough = PassThroughMetric
pass_through_metric = PassThroughMetric


class SklearnMetric(ModularMetric):
    """A subclass of ModularMetric where you can pass in a string name of a metric from
    sklrean.metrics, and BOA will grab that metric and create a BOA metric class for you.

    See Also
    ========
    :external:py:mod:`sklearn.metrics`
        for the list of metrics you can use.
    :class:`.ModularMetric`
        For information on all parameters various metrics in general can be supplied
    """

    def __init__(self, metric_to_eval: str = None, *args, **kwargs):
        if isinstance(metric_to_eval, str):
            kwargs["to_eval_name"] = metric_to_eval
            metric_to_eval = get_sklearn_func(metric_to_eval)
        super().__init__(metric_to_eval=metric_to_eval, *args, **kwargs)


class MeanSquaredError(SklearnMetric):
    """
    Mean squared error regression loss.

    See Also
    ========
    :external:py:func:`sklearn.metrics.mean_squared_error`
        for the function parameters to guide your json attribute-value pairs needed.
    :class:`.ModularMetric`
        For information on all parameters various metrics in general can be supplied
    """

    _metric_to_eval = "mean_squared_error"

    def __init__(self, lower_is_better=True, *args, **kwargs):
        super().__init__(lower_is_better=lower_is_better, *args, **kwargs)


MSE = MeanSquaredError
mean_squared_error = MSE


class RootMeanSquaredError(SklearnMetric):
    """
    Root mean squared error regression loss.

    See Also
    ========
    :external:py:func:`sklearn.metrics.mean_squared_error`
        with  squared=False for the function parameters to guide your json attribute-value pairs needed.
    :class:`.ModularMetric`
        For information on all parameters various metrics in general can be supplied
    """

    _metric_to_eval = "mean_squared_error"

    def __init__(
        self,
        lower_is_better=True,
        metric_func_kwargs=(("squared", False),),
        *args,
        **kwargs,
    ):
        if metric_func_kwargs == (("squared", False),):
            metric_func_kwargs = dict((y, x) for x, y in metric_func_kwargs)
        super().__init__(
            lower_is_better=lower_is_better,
            metric_func_kwargs=metric_func_kwargs,
            *args,
            **kwargs,
        )


RMSE = RootMeanSquaredError
root_mean_squared_error = RMSE


class RSquared(SklearnMetric):
    """
    :math:`R^2` (coefficient of determination) regression score function.

    Best possible score is 1.0, and it can be negative (because the
    model can be arbitrarily worse). In the general case when the true y is
    non-constant, a constant model that always predicts the average y
    disregarding the input features would get a :math:`R^2` score of 0.0.

    See Also
    ========
    :external:py:func:`sklearn.metrics.r2_score`
        for the function parameters to guide your json attribute-value pairs needed.
    :class:`.ModularMetric`
        For information on all parameters various metrics in general can be supplied
    """

    _metric_to_eval = "r2_score"

    def __init__(self, lower_is_better=True, *args, **kwargs):
        super().__init__(lower_is_better=lower_is_better, *args, **kwargs)


r2_score = RSquared
R2 = RSquared


class Mean(ModularMetric):
    """
    Arithmetic mean along the specified axis for your metric,
    Defaults to minimization, if you want to maximize,
    specify lower_is_better: False or minimize: False in your configuration

    See Also
    ========
    :external:py:func:`numpy.mean`
        for the function parameters to guide your json attribute-value pairs needed.
    :class:`.ModularMetric`
        For information on all parameters various metrics in general can be supplied
    """

    _metric_to_eval = np.mean

    def __init__(self, lower_is_better=True, *args, **kwargs):
        super().__init__(lower_is_better=lower_is_better, *args, **kwargs)


mean = Mean


class NormalizedRootMeanSquaredError(ModularMetric):
    """
    Normalized root mean squared error. Like a normalized version of RMSE.
    Normalization defaults to IQR (inner quartile range).

    normalized_root_mean_squared_error

    See Also
    ========
    :func:`.normalized_root_mean_squared_error`
        for the function parameters to guide your json attribute-value pairs needed.
    :class:`.ModularMetric`
        For information on all parameters various metrics in general can be supplied
    """

    _metric_to_eval = normalized_root_mean_squared_error_

    def __init__(self, lower_is_better=True, *args, **kwargs):
        super().__init__(lower_is_better=lower_is_better, *args, **kwargs)


NRMSE = NormalizedRootMeanSquaredError
normalized_root_mean_squared_error = NormalizedRootMeanSquaredError

success = []


def get_metric_from_config(config, instantiate=True, **kwargs):
    if config.get("metric") and isinstance(config["metric"], dict):  # backwards compatibility format
        config = config["metric"]
    # If no name is defined, parse out the name to whatever metric they are defining
    if "name" not in config and "name" not in kwargs:
        kwargs["name"] = (
            config.get("metric")
            or config.get("boa_metric")
            or config.get("sklearn_metric")
            or config.get("synthetic_metric")
        )
    if config.get("boa_metric") or config.get("metric"):
        kwargs["metric_name"] = config.get("boa_metric") or config.get("metric")
        metric = get_metric_by_class_name(instantiate=instantiate, **config, **kwargs)
    elif config.get("sklearn_metric"):
        kwargs["metric_name"] = config["sklearn_metric"]
        kwargs["sklearn_"] = True
        metric = get_metric_by_class_name(instantiate=instantiate, **config, **kwargs)
    elif config.get("synthetic_metric"):
        metric = setup_synthetic_metric(instantiate=instantiate, **config, **kwargs)
    elif config["name"]:  # only name but no metric type
        metric = PassThroughMetric(**config, **kwargs)
    else:
        # TODO link to docs for configuration when it exists
        raise KeyError("No valid configuration for metric found.")
    return metric


def get_metric_by_class_name(metric_name, instantiate=True, sklearn_=False, **kwargs):
    if sklearn_:
        return setup_sklearn_metric(metric_name, instantiate=True, **kwargs)
    return (
        get_boa_metric(metric_name)(**{"name": metric_name, **kwargs}) if instantiate else get_boa_metric(metric_name)
    )


def get_boa_metric(name) -> Type[ModularMetric]:
    try:
        m = globals()[name]
        if issubclass(m, ModularMetric):
            return m
        raise KeyError
    except KeyError:
        raise ValueError(f"Invalid Metric Name specified: {name}")


def _get_boa_metric_any_case(name: str):
    try:
        metric_name = [metric for metric in globals() if metric.lower() == name.lower()][0]
    except IndexError:
        get_boa_metric("THIS WILL RAISE THE RIGHT ERROR IN GET BOA METRIC")
    return get_boa_metric(metric_name)
