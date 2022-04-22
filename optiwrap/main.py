import datetime as dt
import logging
import time
from pathlib import Path

import click
from ax import Experiment, Objective, OptimizationConfig
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.service.scheduler import Scheduler, SchedulerOptions

from optiwrap.ax_instantiation_utils import instantiate_search_space_from_json
from optiwrap.metrics import MSE
from optiwrap.runner import WrappedJobRunner
from optiwrap.utils import get_dictionary_from_callable
from optiwrap.wrapper import BaseWrapper
from optiwrap.wrapper_utils import make_experiment_dir, read_experiment_config

# Set up logging


def make_fetch_experiment_with_runner_and_metric(
    ex_settings, search_space_params, wrapper
) -> Experiment:

    # Taking command line arguments for path of config file, input data, and output directory

    # use default options if invalid command line arguments are given

    search_space = instantiate_search_space_from_json(search_space_params, [])

    objective = Objective(
        metric=MSE(name=ex_settings["objective_name"], wrapper=wrapper), minimize=True
    )

    return Experiment(
        search_space=search_space,
        optimization_config=OptimizationConfig(objective=objective),
        runner=WrappedJobRunner(wrapper=wrapper),
        # is_test=True,  # Marking this experiment as a test experiment.
        **get_dictionary_from_callable(Experiment.__init__, ex_settings),
    )


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
    experiment_dir = make_experiment_dir(
        config["optimization_options"]["working_dir"],
        config["optimization_options"]["experiment_name"],
    )

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

    wrapper = BaseWrapper(
        ex_settings=config["optimization_options"],
        model_settings=config["model_options"],
        experiment_dir=experiment_dir,
    )

    experiment = make_fetch_experiment_with_runner_and_metric(
        ex_settings=config["optimization_options"],
        search_space_params=config["search_space_parameters"],
        wrapper=wrapper,
    )

    generation_strategy = choose_generation_strategy(
        search_space=experiment.search_space,
        **get_dictionary_from_callable(choose_generation_strategy, config["optimization_options"]),
    )

    scheduler = Scheduler(
        experiment=experiment,
        generation_strategy=generation_strategy,
        options=SchedulerOptions(),
    )

    scheduler.run_n_trials(config["optimization_options"]["ntrials"])

    logging.info("\nTHAT'S ALL FOR NOW FOLKS! THIS SHIT TOOK: %d", time.time() - start)


if __name__ == "__main__":
    main()
