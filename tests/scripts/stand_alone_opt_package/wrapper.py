from __future__ import annotations

import json
import os
from pathlib import Path

from ax import Trial
from stand_alone_model_func import run_branin_from_trial


class Wrapper:
    def __init__(self, config_path: os.PathLike = None, *args, **kwargs):
        self.config = None
        self.model_settings = None
        self.ex_settings = None
        self.experiment_dir = None

        self.data = {}

        if config_path:
            self.config = self.load_config(config_path, *args, **kwargs)

    def load_config(
        self, config_path: os.PathLike, append_timestamp: bool = True, experiment_dir: os.PathLike = None, **kwargs
    ):
        file_path = Path(config_path).expanduser()
        with open(file_path, "r") as f:
            self.config = json.load(f)

        self.ex_settings = self.config["optimization_options"]
        self.model_settings = self.config.get("model_options", {})

        if experiment_dir:
            self.ex_settings["experiment_dir"] = str(experiment_dir)
            self.experiment_dir = Path(experiment_dir)
            self.experiment_dir.mkdir()
            return self.config

        working_dir = {**self.ex_settings, **kwargs}.get("working_dir")
        if not working_dir:
            working_dir = Path.cwd()

        experiment_name = self.ex_settings["experiment"]["name"]

        experiment_dir = Path(working_dir).expanduser() / f"{experiment_name}"
        experiment_dir.mkdir()

        self.ex_settings["working_dir"] = working_dir
        self.ex_settings["experiment_dir"] = experiment_dir
        self.experiment_dir = experiment_dir

        return self.config

    def write_configs(self, trial: Trial) -> None:
        pass

    def run_model(self, trial: Trial) -> None:
        self.data[trial.index] = run_branin_from_trial(trial)

    def set_trial_status(self, trial: Trial) -> None:
        data_exists = self.data.get(trial.index)
        if data_exists:
            trial.mark_completed()

    def fetch_trial_data(self, trial: Trial, metric_properties: dict, metric_name: str, *args, **kwargs) -> dict:
        return dict(a=self.data[trial.index])
