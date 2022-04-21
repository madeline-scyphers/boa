import datetime as dt
import logging
import time
from pathlib import Path

import click
from ax import Experiment, Objective, OptimizationConfig, Trial
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.service.scheduler import Scheduler, SchedulerOptions

from optiwrap import (
    instantiate_search_space_from_json,
    MSE,
    WrappedJobRunner,
    make_experiment_dir,
    read_experiment_config,
    BaseWrapper,
    instantiate_search_space_from_json,
    MSE,
    WrappedJobRunner,
    make_experiment_dir,
    read_experiment_config,
    make_trial_dir,
    write_configs,
    run_model,
    get_trial_dir,
    get_model_obs,
    get_experiment,
    get_scheduler
)
from optiwrap.utils import get_dictionary_from_callable

# Set up logging

import datetime as dt
import logging
import time
from pathlib import Path


import click
from ax import Experiment, Objective, OptimizationConfig
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.service.scheduler import Scheduler, SchedulerOptions

from optiwrap.utils import get_dictionary_from_callable

# Set up logging


class Fetch3Wrapper(BaseWrapper):
    def __init__(self, ex_settings, model_settings, experiment_dir):
        self.ex_settings = ex_settings
        self.model_settings = model_settings
        self.experiment_dir = experiment_dir

    def run_model(self, trial: Trial):

        trial_dir = make_trial_dir(self.experiment_dir, trial.index)

        config_dir = write_configs(trial_dir, trial.arm.parameters, self.model_settings)

        run_model(
            self.ex_settings["model_path"], config_dir, self.ex_settings["data_path"], trial_dir
        )

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

    def fetch_trial_data(self, trial: Trial, *args, **kwargs):

        modelfile = (
            get_trial_dir(self.experiment_dir, trial.index) / self.ex_settings["output_fname"]
        )

        y_pred, y_true = get_model_obs(
            modelfile,
            self.ex_settings["obsfile"],
            self.ex_settings,
            self.model_settings,
            trial.arm.parameters,
        )
        return dict(y_pred=y_pred, y_true=y_true)


@click.command()
@click.option(
    "-f",
    "--config_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default="/Users/madelinescyphers/projs/fetch3_nhl/optimize/opt_model_config.yml",
    help="Path to configuration YAML file.",
)
def main(config_file):
    """This is my docstring

    Args:
        config (os.PathLike): Path to configuration YAML file
    """
    start = time.time()

    config = read_experiment_config(config_file)  # Read experiment config'
    experiment_dir = make_experiment_dir(config["optimization_options"]["working_dir"], config["optimization_options"]["experiment_name"])

    log_format = "%(levelname)s %(asctime)s - %(message)s"
    logging.basicConfig(
        filename=Path(experiment_dir) / "optimization.log",
        filemode="w",
        format=log_format,
        level=logging.DEBUG,
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    logger = logging.getLogger(__file__)

    logger.info("LET'S START THIS SHIT! %s", dt.datetime.now().strftime("%Y%m%dT%H%M%S"))

    wrapper = Fetch3Wrapper(
        ex_settings=config["optimization_options"],
        model_settings=config["model_options"],
        experiment_dir=experiment_dir,
    )

    experiment = get_experiment(config, WrappedJobRunner(wrapper=wrapper), wrapper)

    scheduler = get_scheduler(experiment,
                              scheduler_options=SchedulerOptions(
                                  total_trials=config["optimization_options"]["total_trials"]),
                              config=config)

    scheduler.run_all_trials()

    logging.info("\nTHAT'S ALL FOR NOW FOLKS! THIS SHIT TOOK: %d", time.time() - start)


if __name__ == "__main__":
    main()
