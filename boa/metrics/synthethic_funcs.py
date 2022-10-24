from ax.utils.measurement.synthetic_functions import from_botorch
from botorch.test_functions.synthetic import Hartmann
from torch import Tensor


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
