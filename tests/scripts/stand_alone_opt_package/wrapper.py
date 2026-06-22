from __future__ import annotations

from stand_alone_model_func import run_branin_from_trial

import boa
from boa.ax_api import Trial, TrialStatus


class WrapperStandAlone(boa.BaseWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = {}

    def run_model(self, trial: Trial) -> None:
        self.data[trial.index] = run_branin_from_trial(trial)

    def get_trial_status(self, trial: Trial) -> None:
        data_exists = self.data.get(trial.index) is not None
        if data_exists:
            return TrialStatus.COMPLETED

    def fetch_trial_data(self, trial: Trial, metric_properties: dict, metric_name: str, *args, **kwargs) -> dict:
        # return dict(a=self.data[trial.index])
        return {
            "Mean": {"a": list(trial.arm.parameters.values()), "sem": 4.5},
            "RMSE": {
                "y_true": [1.12, 1.25],
                "y_pred": list(trial.arm.parameters.values()),
            },
        }
