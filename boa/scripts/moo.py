from pathlib import Path

import torch

from boa.controller import Controller
from boa.metrics.synthetic_funcs import get_synth_func
from boa.wrappers.base_wrapper import BaseWrapper

BraninCurrin = get_synth_func("BraninCurrin")
branin_currin = BraninCurrin()


class Wrapper(BaseWrapper):
    def run_model(self, trial) -> None:
        pass

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        evaluation = branin_currin(torch.tensor([trial.arm.parameters.get("x1"), trial.arm.parameters.get("x2")]))
        return {"branin": evaluation[0].item(), "currin": evaluation[1].item()}


def main():
    config_path = Path(__file__).resolve().parent / "moo.yaml"
    wrapper = Wrapper(config_path=config_path)
    controller = Controller(wrapper=wrapper)
    controller.initialize_scheduler()
    return controller.run()


if __name__ == "__main__":
    main()
