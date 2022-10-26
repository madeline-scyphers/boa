from __future__ import annotations

from ax import Trial
from stand_alone_model_func import run_branin_from_trial

from boa.wrappers.wrapper import BaseWrapper


class Wrapper(BaseWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = {}

    def run_model(self, trial: Trial) -> None:
        self.data[trial.index] = run_branin_from_trial(trial)

    def set_trial_status(self, trial: Trial) -> None:
        data_exists = self.data.get(trial.index)
        if data_exists:
            trial.mark_completed()

    def fetch_trial_data(self, trial: Trial, metric_properties: dict, metric_name: str, *args, **kwargs) -> dict:
        return dict(a=self.data[trial.index])
