import tempfile
from pathlib import Path

import torch

from boa.controller import Controller
from boa.metrics.synthetic_funcs import get_synth_func
from boa.utils import torch_device
from boa.wrappers.base_wrapper import BaseWrapper

tkwargs = {
    "device": torch_device(),
}
Problem = get_synth_func("BraninCurrin")

problem = Problem(negate=True).to(**tkwargs)


class WrapperMoo(BaseWrapper):
    def run_model(self, trial) -> None:
        pass

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        evaluation = problem(torch.tensor([trial.arm.parameters["x0"], trial.arm.parameters["x1"]]))
        a = float(evaluation[0])
        b = float(evaluation[1])
        return {"branin": a, "currin": b}


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        experiment_dir = Path(temp_dir)
        config_path = Path(__file__).resolve().parent / "moo.yaml"
        wrapper = WrapperMoo(config_path=config_path, experiment_dir=experiment_dir)
        controller = Controller(wrapper=wrapper)
        controller.initialize_scheduler()
        return controller.run()


if __name__ == "__main__":
    main()
