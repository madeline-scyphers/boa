from pathlib import Path

import numpy as np
from ax.service.utils.report_utils import exp_to_df

from boa.controller import Controller
from boa.wrappers.base_wrapper import BaseWrapper


class Wrapper(BaseWrapper):
    def run_model(self, trial) -> None:
        pass

    def set_trial_status(self, trial) -> None:
        trial.mark_completed()

    def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        idx = trial.index + 1
        return {
            "Meanyyy": {"a": idx * np.array([-0.3691, 4.6544, 1.2675, -0.4327]), "sem": 4.5},
            "RMSE": {
                "y_true": idx * np.array([1.12, 1.25, 2.54, 4.52]),
                "y_pred": idx * np.array([1.51, 1.01, 2.21, 4.50]),
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
