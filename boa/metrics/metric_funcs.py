"""
########################
Metric Functions
########################

Functions used for Metrics

"""
from __future__ import annotations

import numpy as np
import scipy.stats as stats
import sklearn.metrics
from sklearn.metrics import __all__ as sklearn_all
from sklearn.metrics import mean_squared_error

from boa.logger import get_logger
from boa.utils import get_dictionary_from_callable

logger = get_logger()


def normalized_root_mean_squared_error(y_true, y_pred, normalizer="iqr", **kwargs):
    """Normalized root mean squared error

    Parameters
    ----------
    y_true : array_like
        With shape (n_samples,) or (n_samples, n_outputs)
        Ground truth (correct) target values.

    y_pred : array_like
        With shape (n_samples,) or (n_samples, n_outputs)
        Estimated target values.

    normalizer : str
        How to normalize the RMSE, options include iqr, std, mean, and range.
        (default iqr)

    **kwargs
        see sklearn.metrics.mean_squared_error for additional options

    Returns
    -------
    nrmse : float or numpy.ndarray[float]
        A normalized version of RMSE
    """
    rmse = mean_squared_error(y_true, y_pred, squared=False, **get_dictionary_from_callable(mean_squared_error, kwargs))
    if normalizer == "iqr":
        norm = stats.iqr(y_pred)
    elif normalizer == "std":
        norm = stats.tstd(y_pred)
    elif normalizer == "mean":
        norm = stats.tmean(y_pred)
    elif normalizer == "range":
        norm = np.ptp(y_pred)
    else:
        raise ValueError("normalizer must be 'iqr', 'std', 'mean', or 'range'.")

    nrmse = rmse / norm
    return nrmse


def setup_sklearn_metric(metric_to_eval, instantiate=True, **kw):
    import boa.metrics.metrics

    def modular_sklearn_metric(**kwargs):
        return boa.metrics.metrics.SklearnMetric(
            **{"name": metric_to_eval, **kw, **kwargs, "metric_to_eval": metric_to_eval}
        )

    return modular_sklearn_metric(**kw) if instantiate else modular_sklearn_metric


def get_sklearn_func(metric_to_eval):
    if metric_to_eval in sklearn_all:
        metric = getattr(sklearn.metrics, metric_to_eval)
    # we also check the attribute name incase metric_to_eval is actual a class b/c ModularMetric
    # has been cloned
    elif getattr(metric_to_eval, "name", None) in sklearn_all:
        metric = getattr(sklearn.metrics, metric_to_eval.name)
    else:
        raise AttributeError(f"Sklearn metric: {metric_to_eval} not found!")
    return metric
