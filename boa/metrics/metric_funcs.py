import logging

import numpy as np
import scipy.stats as stats
from sklearn.metrics import mean_squared_error

from boa._doc_utils import add_ref_to_rel_init
from boa.utils import get_dictionary_from_callable

logger = logging.getLogger(__name__)


def normalized_root_mean_squared_error(y_true, y_pred, normalizer="iqr", **kwargs):
    """Normalized root mean squared error

    Parameters
    ----------
    y_true : array-like of shape (n_samples,) or (n_samples, n_outputs)
        Ground truth (correct) target values.

    y_pred : array-like of shape (n_samples,) or (n_samples, n_outputs)
        Estimated target values.

    normalizer : str
        How to normalize the RMSE, options include iqr, std, mean, and range.
        (default iqr)

    **kwargs
        see sklearn.metrics.mean_squared_error for additional options

    Returns
    -------
    nrmse : float or ndarray of floats
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


__doc__ = f"""
########################
Metric Functions
########################

Functions used for Metrics

{add_ref_to_rel_init()}
"""
