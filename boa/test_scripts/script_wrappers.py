import json
import os
import subprocess

import numpy as np
from ax import Trial

from boa import (
    BaseWrapper,
    cd_and_cd_back_dec,
    get_synth_func,
    get_trial_dir,
    make_trial_dir,
)
from boa.definitions import TEST_SCRIPTS_DIR


class Wrapper(BaseWrapper):
    _processes = []
    # Use default BaseWrapper methods for everything but methods below

    @cd_and_cd_back_dec(path=TEST_SCRIPTS_DIR)
    def run_model(self, trial: Trial):
        trial_dir = make_trial_dir(self.experiment_dir, trial.index).resolve()

        model_dir = self.model_settings["model_dir"]

        os.chdir(model_dir)

        cmd = (
            f"python synth_func_cli.py --output_dir {trial_dir}"
            f" --standard_dev {self.ex_settings['objective_options']['objectives'][0]['noise_sd']}"
            f" --input_size {self.model_settings['input_size']}"
            f" -- {' '.join(str(val) for val in trial.arm.parameters.values())}"
        )

        args = cmd.split()
        popen = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True)
        self._processes.append(popen)

    def set_trial_status(self, trial: Trial) -> None:
        output_file = get_trial_dir(self.experiment_dir, trial.index) / "output.json"

        if output_file.exists():
            trial.mark_completed()

    def fetch_trial_data(self, trial: Trial, *args, **kwargs):
        output_file = get_trial_dir(self.experiment_dir, trial.index) / "output.json"
        with open(output_file, "r") as f:
            data = json.load(f)

        return dict(
            y_true=np.full(
                self.model_settings["input_size"],
                get_synth_func("branin").fmin,
            ),
            y_pred=data["output"],
        )


def exit_handler():
    for process in Wrapper._processes:
        process.kill()
