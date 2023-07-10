import numpy as np
from ax.utils.measurement.synthetic_functions import from_botorch
from botorch.test_functions.synthetic import Cosine8

import boa

cosine8 = from_botorch(Cosine8())


def black_box_model(X) -> float:
    result = -cosine8(X)
    return result


class Wrapper(boa.BaseWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = {}

    def run_model(self, trial) -> None:
        X = np.array([parameter for parameter in trial.arm.parameters.values()])
        # This is a silly toy function, in reality,
        # you could instead import your model main() function and use that, and then collect the results.
        # You could also call an external script to start a model run from Bash or elsewhere.
        self.data[trial.index] = black_box_model(X)

    def set_trial_status(self, trial) -> None:
        data_exists = self.data.get(trial.index)
        if data_exists:
            trial.mark_completed()

    def fetch_trial_data(self, trial, *args, **kwargs):
        return self.data[trial.index]
