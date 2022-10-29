import json
import os
import subprocess
from pathlib import Path

import numpy as np
from ax import Trial

import boa
from boa.definitions import TEST_SCRIPTS_DIR


class Wrapper(boa.BaseWrapper):
    _processes = []
    # Use default BaseWrapper methods for everything but methods below

    @boa.cd_and_cd_back_dec(path=TEST_SCRIPTS_DIR)
    def run_model(self, trial: Trial):
        trial_dir = boa.make_trial_dir(self.experiment_dir, trial.index).resolve()

        model_dir = Path(__file__).resolve().parent.parent.parent

        os.chdir(model_dir)

        cmd = (
            f"python -m boa.test_scripts.synth_func_cli --output_dir {trial_dir}"
            f" --standard_dev {self.ex_settings['objective_options']['objectives'][0]['noise_sd']}"
            f" --input_size {self.model_settings['input_size']}"
            f" -- {' '.join(str(val) for val in trial.arm.parameters.values())}"
        )

        args = cmd.split()
        popen = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True)
        self._processes.append(popen)

    def set_trial_status(self, trial: Trial) -> None:
        output_file = boa.get_trial_dir(self.experiment_dir, trial.index) / "output.json"

        if output_file.exists():
            trial.mark_completed()

    def fetch_trial_data(self, trial: Trial, *args, **kwargs):
        output_file = boa.get_trial_dir(self.experiment_dir, trial.index) / "output.json"
        with open(output_file, "r") as f:
            data = json.load(f)

        return dict(
            y_true=np.full(
                self.model_settings["input_size"],
                boa.get_synth_func("branin").fmin,
            ),
            y_pred=data["output"],
        )


def exit_handler():
    for process in Wrapper._processes:
        process.kill()
