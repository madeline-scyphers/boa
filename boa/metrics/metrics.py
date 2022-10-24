import numpy as np

from boa.metrics.metric_funcs import (
    normalized_root_mean_squared_error as normalized_root_mean_squared_error_,
)
from boa.metrics.modular_metric import ModularMetric, SklearnMetric


class MeanSquaredError(SklearnMetric):
    """
    Mean squared error regression loss. Read more from sklearn mean squared error
    """

    def __init__(self, metric_to_eval="mean_squared_error", lower_is_better=True, *args, **kwargs):
        super().__init__(metric_to_eval=metric_to_eval, lower_is_better=lower_is_better, *args, **kwargs)


MSE = MeanSquaredError
mean_squared_error = MSE


class RootMeanSquaredError(SklearnMetric):
    """
    Root mean squared error regression loss. Read more from sklearn mean squared error with squared=False
    """

    def __init__(
        self,
        metric_to_eval="mean_squared_error",
        lower_is_better=True,
        metric_func_kwargs=(("squared", False),),
        *args,
        **kwargs
    ):
        if metric_func_kwargs == (("squared", False),):
            metric_func_kwargs = dict((y, x) for x, y in metric_func_kwargs)
        super().__init__(
            metric_to_eval=metric_to_eval,
            lower_is_better=lower_is_better,
            metric_func_kwargs=metric_func_kwargs,
            *args,
            **kwargs
        )


RMSE = RootMeanSquaredError
root_mean_squared_error = RMSE


class RSquared(SklearnMetric):
    """
    :math:`R^2` (coefficient of determination) regression score function.

    Best possible score is 1.0 and it can be negative (because the
    model can be arbitrarily worse). In the general case when the true y is
    non-constant, a constant model that always predicts the average y
    disregarding the input features would get a :math:`R^2` score of 0.0.
    """

    def __init__(self, metric_to_eval="mean_squared_error", lower_is_better=True, *args, **kwargs):

        super().__init__(metric_to_eval=metric_to_eval, lower_is_better=lower_is_better, *args, **kwargs)


r2_score = RSquared
R2 = RSquared


class Mean(ModularMetric):
    """
    Arithmetic mean along the specified axis for your metric,
    Defaults to minimizization, if you want to maximize,
    specify lower_is_better: False or minimize: False in your configuration
    """

    def __init__(self, metric_to_eval=np.mean, lower_is_better=True, *args, **kwargs):

        super().__init__(metric_to_eval=metric_to_eval, lower_is_better=lower_is_better, *args, **kwargs)


mean = Mean


class NormalizedRootMeanSquaredError(ModularMetric):
    """
    Normalized root mean squared error. Like a normalized version of RMSE.
    Normalization defaults to IQR (inner quartile range).
    """

    def __init__(self, metric_to_eval=normalized_root_mean_squared_error_, lower_is_better=True, *args, **kwargs):

        super().__init__(metric_to_eval=metric_to_eval, lower_is_better=lower_is_better, *args, **kwargs)


NRMSE = NormalizedRootMeanSquaredError
normalized_root_mean_squared_error = NormalizedRootMeanSquaredError
