from __future__ import annotations

from typing import Optional
from ax import Experiment, Trial
from ax.core.base_trial import BaseTrial

from wrapper_utils import make_trial_dir, write_configs, run_model, get_trial_dir, get_model_obs


class Wrapper:
    def __init__(self, params, ex_settings, model_settings, experiment_dir):
        # self.params = params
        self.ex_settings = ex_settings
        self.model_settings = model_settings
        self.experiment_dir = experiment_dir

    def run_model(self, trial: Trial):

        trial_dir = make_trial_dir(self.experiment_dir, trial.index)

        config_dir = write_configs(trial_dir, trial.arm.parameters, self.model_settings)

        run_model(self.ex_settings['model_path'], config_dir, self.ex_settings['data_path'], trial_dir)

    def set_trial_status(self, trial: Trial) -> None:
        """ "Get status of the job by a given ID. For simplicity of the example,
        return an Ax `TrialStatus`.
        """
        log_file = get_trial_dir(self.experiment_dir, trial.index) / "fetch3.log"

        if log_file.exists():
            with open(log_file, "r") as f:
                contents = f.read()
            if "run complete" in contents:
                trial.mark_completed()

    def fetch_trial_data(self, trial: BaseTrial, *args, **kwargs):

        modelfile = get_trial_dir(self.experiment_dir, trial.index) / self.ex_settings['output_fname']

        y_pred, y_true = get_model_obs(modelfile, self.ex_settings['obsfile'], self.ex_settings, self.model_settings, trial.arm.parameters)
        return dict(y_pred=y_pred, y_true=y_true)
