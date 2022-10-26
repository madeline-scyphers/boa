"""
########################
List of Metrics
########################

List of Metrics that are already defined in BOA

Any of these Metrics can be used directly in your configuration file

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

"""
from __future__ import annotations

import numpy as np

from boa.metrics.metric_funcs import get_sklearn_func
from boa.metrics.metric_funcs import (
    normalized_root_mean_squared_error as normalized_root_mean_squared_error_,
)
from boa.metrics.metric_funcs import setup_sklearn_metric
from boa.metrics.modular_metric import ModularMetric
from boa.metrics.synthetic_funcs import setup_synthetic_metric


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

    def __init__(self, metric_to_eval: str, *args, **kwargs):
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

    def __init__(self, metric_to_eval="mean_squared_error", lower_is_better=True, *args, **kwargs):
        super().__init__(metric_to_eval=metric_to_eval, lower_is_better=lower_is_better, *args, **kwargs)


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

    def __init__(
        self,
        metric_to_eval="mean_squared_error",
        lower_is_better=True,
        metric_func_kwargs=(("squared", False),),
        *args,
        **kwargs,
    ):
        if metric_func_kwargs == (("squared", False),):
            metric_func_kwargs = dict((y, x) for x, y in metric_func_kwargs)
        super().__init__(
            metric_to_eval=metric_to_eval,
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

    def __init__(self, metric_to_eval="r2_score", lower_is_better=True, *args, **kwargs):
        super().__init__(metric_to_eval=metric_to_eval, lower_is_better=lower_is_better, *args, **kwargs)


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

    def __init__(self, metric_to_eval=np.mean, lower_is_better=True, *args, **kwargs):
        super().__init__(metric_to_eval=metric_to_eval, lower_is_better=lower_is_better, *args, **kwargs)


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

    def __init__(self, metric_to_eval=normalized_root_mean_squared_error_, lower_is_better=True, *args, **kwargs):
        super().__init__(metric_to_eval=metric_to_eval, lower_is_better=lower_is_better, *args, **kwargs)


NRMSE = NormalizedRootMeanSquaredError
normalized_root_mean_squared_error = NormalizedRootMeanSquaredError


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


def get_boa_metric(name):
    try:
        return globals()[name]
    except KeyError:
        raise ValueError(f"Invalid Metric Name specified: {name}")
