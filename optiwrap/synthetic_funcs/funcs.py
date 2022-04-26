import numpy as np
from ax.utils.common.docutils import copy_doc
from ax.utils.measurement.synthetic_functions import from_botorch
from botorch.test_functions.synthetic import Ackley

ackley = from_botorch(Ackley(dim=4))


def map_range(value, old_min, old_max, new_min, new_max):
    OldRange = old_max - old_min
    NewRange = new_max - new_min
    return (((value - old_min) * NewRange) / OldRange) + new_min


class FakePalm(ackley):
    @copy_doc(ackley._f)
    def _f(self, X: np.ndarray) -> float:

        X[0] = map_range(X[0], 350, 950, -32.768, 32.768)
        X[1] = map_range(X[1], 0.15, 0.9, -32.768, 32.768)
        X[2] = map_range(X[2], 0.25, 0.8, -32.768, 32.768)
        X[3] = map_range(X[3], 2.0, 6.0, -32.768, 32.768)

        return super()._f(X)

        # -32.768, 32.768

        #     "plot_footprint": 350 - 950
        #     "house_ratio": .15 - .9
        #     "ground_ratio": .25 - .8
        #     "mean_lai": 2.0 - 6.0
