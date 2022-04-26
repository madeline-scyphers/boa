import numpy as np
from ax.utils.measurement.synthetic_functions import from_botorch
from botorch.test_functions.synthetic import Ackley
from torch import Tensor


def map_range(value, old_min, old_max, new_min, new_max):
    OldRange = old_max - old_min
    NewRange = new_max - new_min
    return (((value - old_min) * NewRange) / OldRange) + new_min


class FakePalm(Ackley):
    def __init__(self, *args, **kwargs):
        dim = 4
        super().__init__(dim=dim, *args, **kwargs)
    def evaluate_true(self, X: Tensor) -> float:
        X[..., 0] = map_range(X[..., 0], 350, 950, -32.768, 32.768)
        X[..., 1] = map_range(X[..., 1], 0.15, 0.9, -32.768, 32.768)
        X[..., 2] = map_range(X[..., 2], 0.25, 0.8, -32.768, 32.768)
        X[..., 3] = map_range(X[..., 3], 2.0, 6.0, -32.768, 32.768)

        return super().evaluate_true(X)

fake_palm = from_botorch(FakePalm())
