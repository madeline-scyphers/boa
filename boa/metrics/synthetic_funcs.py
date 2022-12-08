"""
########################
Synthetic Function
########################

"""
from __future__ import annotations

import sys
from inspect import isclass

import ax.utils
import botorch.test_functions
from ax.utils.measurement.synthetic_functions import from_botorch
from botorch.test_functions.synthetic import Hartmann
from torch import Tensor

from boa.metrics.modular_metric import ModularMetric


class Hartmann4(Hartmann):
    dim = 4

    def __init__(self, *args, **kwargs):
        super().__init__(dim=self.dim, *args, **kwargs)
        self._optimizers = [(0.1873, 0.1906, 0.5566, 0.2647)]
        self._optimal_value = 2.864526

    @property
    def optimal_value(self) -> float:
        return super().optimal_value

    @property
    def optimizers(self) -> Tensor:
        return super().optimizers


hartmann4 = from_botorch(Hartmann4())


def get_synth_func(
    synthetic_metric: str,
) -> (
    botorch.test_functions.synthetic.SyntheticTestFunction | ax.utils.measurement.synthetic_functions.SyntheticFunction
):
    synthetic_funcs_modules = [
        sys.modules[__name__],  # this module
        ax.utils.measurement.synthetic_functions,
        botorch.test_functions.synthetic,
    ]
    for module in synthetic_funcs_modules:
        try:
            return getattr(module, synthetic_metric)
        except AttributeError:
            continue
    # If we don't find the class by the end of the modules, raise attribute error
    raise AttributeError(f"boa synthetic function: {synthetic_metric} not found in modules: {synthetic_funcs_modules}!")


def setup_synthetic_metric(synthetic_metric, instantiate=True, **kw):
    metric = get_synth_func(synthetic_metric)

    if isclass(metric) and issubclass(metric, ax.utils.measurement.synthetic_functions.SyntheticFunction):
        metric = metric()  # if they pass a ax synthetic metric class, not instance
    elif isclass(metric) and issubclass(metric, botorch.test_functions.synthetic.SyntheticTestFunction):
        # botorch synthetic functions need to be converted
        metric = from_botorch(botorch_synthetic_function=metric())

    def modular_synthetic_metric(**kwargs):
        return ModularMetric(**{"name": synthetic_metric, **kw, **kwargs, "metric_to_eval": metric})

    return modular_synthetic_metric(**kw) if instantiate else modular_synthetic_metric
