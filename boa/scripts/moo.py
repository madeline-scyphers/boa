from pathlib import Path

import numpy as np

from boa.controller import Controller
from boa.metrics.synthetic_funcs import get_synth_func
from boa.wrappers.base_wrapper import BaseWrapper

hartmann6 = get_synth_func("hartmann6")


class Wrapper(BaseWrapper):
    def run_model(self, trial) -> None:
        pass

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        val = hartmann6(np.array(list(trial.arm.parameters.values())))

        return {
            "Meanyyy": {"a": val},
            "RMSE": {
                "y_true": hartmann6.fmin,
                "y_pred": val,
            },
        }


def main():
    config_path = Path(__file__).resolve().parent / "moo.yaml"
    wrapper = Wrapper(config_path=config_path)
    controller = Controller(wrapper=wrapper)
    controller.initialize_scheduler()
    return controller.run()


if __name__ == "__main__":
    main()
