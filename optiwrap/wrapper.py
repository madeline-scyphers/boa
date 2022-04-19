from __future__ import annotations

from abc import ABC

from ax import Trial
from ax.core.base_trial import BaseTrial

from optiwrap.wrapper_utils import (
    get_model_obs,
    get_trial_dir,
    make_trial_dir,
    run_model,
    write_configs,
)


class BaseWrapper(ABC):
    def run_model(self, trial: Trial):
        pass

    def set_trial_status(self, trial: Trial) -> None:
        pass

    def fetch_trial_data(self, trial: BaseTrial, *args, **kwargs):
        pass
