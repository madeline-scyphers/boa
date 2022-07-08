import json
import os
import subprocess
from pathlib import Path

import numpy as np
from ax import Trial

from boa import (
    BaseWrapper,
    cd_and_cd_back_dec,
    get_synth_func,
    get_trial_dir,
    make_trial_dir,
)
from boa.definitions import ROOT


class TestWrapper(BaseWrapper):
    _processes = []

    def __init__(self, ex_settings, experiment_dir, model_settings):
        self.ex_settings = ex_settings
        self.experiment_dir = experiment_dir
        self.model_settings = model_settings

    @cd_and_cd_back_dec(path=ROOT)
    def run_model(self, trial: Trial):
        trial_dir = make_trial_dir(self.experiment_dir, trial.index).resolve()

        model_dir = self.ex_settings["model_dir"]

        os.chdir(model_dir)

        cmd = (
            f"python synth_func_cli.py --output_dir {trial_dir}"
            f" --standard_dev {self.ex_settings['objective_options']['objectives'][0]['noise_sd']}"
            f" --input_size {self.model_settings['input_size']}"
            f" --function {self.model_settings['function']}"
            f" -- {' '.join(str(val) for val in trial.arm.parameters.values())}"
        )

        args = cmd.split()
        popen = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True)
        self._processes.append(popen)

    def set_trial_status(self, trial: Trial) -> None:
        """ "Get status of the job by a given ID. For simplicity of the example,
        return an Ax `TrialStatus`.
        """
        output_file = get_trial_dir(self.experiment_dir, trial.index) / "output.json"

        if output_file.exists():
            trial.mark_completed()

    def fetch_trial_data(self, trial: Trial, *args, **kwargs):
        output_file = get_trial_dir(self.experiment_dir, trial.index) / "output.json"
        with open(output_file, "r") as f:
            data = json.load(f)

        # return dict(a=data["output"])
        # return dict(y_true=[hartmann6.fmin], y_pred=[np.mean(data["output"])])
        return dict(
            y_true=np.full(
                self.model_settings["input_size"],
                get_synth_func(self.model_settings["function"]).fmin,
            ),
            y_pred=data["output"],
        )


def exit_handler():
    for process in TestWrapper._processes:
        process.kill()
