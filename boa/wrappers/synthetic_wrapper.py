from __future__ import annotations

from typing import Any, Sequence

from ax import Trial

from boa.wrappers.base_wrapper import BaseWrapper


class SyntheticWrapper(BaseWrapper):
    def __init__(self, *args, metrics: dict[str, Sequence] | Sequence | Any = None, fetch_none_ok=True, **kwargs):
        self._metrics = metrics
        super().__init__(*args, fetch_none_ok=fetch_none_ok, **kwargs)

    def run_model(self, trial: Trial) -> None:
        pass

    def set_trial_status(self, trial: Trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(
        self,
        metric_name: str,
        trial: Trial,
        **kwargs,
    ):
        if isinstance(self._metrics, dict):
            return self._metrics[metric_name][trial.index]
        else:
            return self._metrics
