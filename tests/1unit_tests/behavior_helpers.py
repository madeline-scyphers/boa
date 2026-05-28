from pathlib import Path

from boa import BOAConfig
from boa.client import get_client
from boa.wrappers.base_wrapper import BaseWrapper


class DeterministicWrapper(BaseWrapper):
    def __init__(self, *args, **kwargs):
        self.values = {}
        super().__init__(*args, **kwargs)

    def run_model(self, trial):
        self.values[trial.index] = sum(float(value) for value in trial.arm.parameters.values())

    def set_trial_status(self, trial):
        trial.mark_completed()

    def fetch_trial_data(self, trial, parameters=None, metric_name=None, **kwargs):
        if trial.index not in self.values:
            self.values[trial.index] = sum(float(value) for value in trial.arm.parameters.values())
        return self.values[trial.index]


class InitArgObject:
    def __init__(self, public=1, private=2):
        self.public = public
        self._private = private


def parse_int_string(value):
    if value.isdigit():
        return int(value)
    return value


def passthrough_config(experiment_dir, n_trials=2, metric_name="metric"):
    return BOAConfig(
        optimization={
            "objective": metric_name,
            "metrics": {metric_name: {"metric_type": "passthrough", "minimize": True}},
        },
        generation_strategy={"method": "fast", "initialization_budget": max(n_trials, 1)},
        orchestrator={"total_trials": n_trials, "max_pending_trials": 1},
        parameters={
            "x": {"type": "range", "bounds": [0.0, 1.0], "parameter_type": "float"},
            "fixed": {"type": "fixed", "value": 1.0, "parameter_type": "float"},
        },
        n_trials=n_trials,
        script_options={
            "experiment_dir": str(Path(experiment_dir)),
            "append_timestamp": False,
            "exp_name": "real_behavior_test",
        },
    )


def deterministic_wrapper(experiment_dir, n_trials=2):
    config = passthrough_config(experiment_dir=experiment_dir, n_trials=n_trials)
    return DeterministicWrapper(config=config, experiment_dir=experiment_dir, append_timestamp=False)


def deterministic_client(experiment_dir, n_trials=2):
    wrapper = deterministic_wrapper(experiment_dir=experiment_dir, n_trials=n_trials)
    client = get_client(config=wrapper.config, wrapper=wrapper)
    return client, wrapper
