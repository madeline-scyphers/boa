import numpy as np

from boa.wrappers.base_wrapper import BaseWrapper


class Wrapper(BaseWrapper):
    def __init__(self, *args, fetch_all=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fetch_all = fetch_all

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        if self.fetch_all:
            idx = trial.index + 1
            return {
                "Meanyyy": {"a": idx * np.array([-0.3691, 4.6544, 1.2675, -0.4327]), "sem": 4.5},
                "RMSE": {
                    "y_true": idx * np.array([1.12, 1.25, 2.54, 4.52]),
                    "y_pred": idx * np.array([1.51, 1.01, 2.21, 4.50]),
                },
            }
        else:
            idx = trial.index + 1
            if metric_name == "Meanyyy":
                return {"a": idx * np.array([-0.3691, 4.6544, 1.2675, -0.4327]), "sem": 4.5}
            elif metric_name == "RMSE":
                return {
                    "y_true": idx * np.array([1.12, 1.25, 2.54, 4.52]),
                    "y_pred": idx * np.array([1.51, 1.01, 2.21, 4.50]),
                }