import datetime as dt
import logging
import time
from pathlib import Path

import click
from ax import Experiment, Objective, OptimizationConfig, Trial
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.service.scheduler import Scheduler, SchedulerOptions

from fetch_wrapper import Fetch3Wrapper2 as Fetch3Wrapper
from optiwrap import (
    BaseWrapper,
    ModularMetric,
    WrappedJobRunner,
    get_experiment,
    get_model_obs,
    get_scheduler,
    get_trial_dir,
    instantiate_search_space_from_json,
    make_experiment_dir,
    make_trial_dir,
    load_experiment_config,
    run_model,
    write_configs,
)
from optiwrap.metrics.metric_funcs import metric_from_json
from optiwrap.utils import get_dictionary_from_callable


@click.command()
@click.option(
    "-f",
    "--config_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default="/Users/madelinescyphers/projs/fetch3_nhl/optimize/optiwrap_config2.yaml",
    help="Path to configuration YAML file.",
)
def main(config_file):
    """This is my docstring

    Args:
        config (os.PathLike): Path to configuration YAML file
    """
    start = time.time()

    config = load_experiment_config(config_file)  # Read experiment config'
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

    logger.info("Start time: %s", dt.datetime.now().strftime("%Y%m%dT%H%M%S"))

    wrapper = Fetch3Wrapper(
        ex_settings=config["optimization_options"],
        model_settings=config["model_options"],
        experiment_dir=experiment_dir,
        main_prog="2"
    )

    experiment = get_experiment(config, WrappedJobRunner(wrapper=wrapper), wrapper)

    scheduler = get_scheduler(experiment, config=config)

    scheduler.run_all_trials()

    logging.info("\nTrials completed! Total run time: %d", time.time() - start)


if __name__ == "__main__":
    main()


# import datetime as dt
# import logging
# import time
# from pathlib import Path

# import click
# from ax import Experiment, Objective, OptimizationConfig, Trial
# from ax.modelbridge.dispatch_utils import choose_generation_strategy
# from ax.service.scheduler import Scheduler, SchedulerOptions

# from optiwrap import (
#     instantiate_search_space_from_json,
#     MSE,
#     WrappedJobRunner,
#     make_experiment_dir,
#     read_experiment_config,
#     BaseWrapper,
#     instantiate_search_space_from_json,
#     MSE,
#     WrappedJobRunner,
#     make_experiment_dir,
#     read_experiment_config,
#     make_trial_dir,
#     write_configs,
#     run_model,
#     get_trial_dir,
#     get_model_obs,
#     get_experiment,
#     get_scheduler
# )
# from optiwrap.utils import get_dictionary_from_callable

# # Set up logging

# import datetime as dt
# import logging
# import time
# from pathlib import Path


# import click
# from ax import Experiment, Objective, OptimizationConfig
# from ax.modelbridge.dispatch_utils import choose_generation_strategy
# from ax.service.scheduler import Scheduler, SchedulerOptions

# from optiwrap.utils import get_dictionary_from_callable
# from fetch_wrapper import Fetch3Wrapper

# @click.command()
# @click.option(
#     "-f",
#     "--config_file",
#     type=click.Path(exists=True, dir_okay=False, path_type=Path),
#     # default="/Users/madelinescyphers/projs/fetch3_nhl/optimize/opt_model_config.yml",
#     default="/Users/madelinescyphers/projs/fetch3_nhl/optimize/optiwrap_config.yaml",
#     help="Path to configuration YAML file.",
# )
# def main(config_file):
#     """This is my docstring

#     Args:
#         config (os.PathLike): Path to configuration YAML file
#     """
#     start = time.time()

#     config = read_experiment_config(config_file)  # Read experiment config'
#     experiment_dir = make_experiment_dir(config["optimization_options"]["working_dir"], config["optimization_options"]["experiment_name"])

#     log_format = "%(levelname)s %(asctime)s - %(message)s"
#     logging.basicConfig(
#         filename=Path(experiment_dir) / "optimization.log",
#         filemode="w",
#         format=log_format,
#         level=logging.DEBUG,
#     )
#     logging.getLogger().addHandler(logging.StreamHandler())
#     logger = logging.getLogger(__file__)

#     logger.info("LET'S START THIS SHIT! %s", dt.datetime.now().strftime("%Y%m%dT%H%M%S"))

#     wrapper = Fetch3Wrapper(
#         ex_settings=config["optimization_options"],
#         model_settings=config["model_options"],
#         experiment_dir=experiment_dir,
#         main_prog="2"
#     )

#     experiment = get_experiment(config, WrappedJobRunner(wrapper=wrapper), wrapper)

#     scheduler = get_scheduler(experiment, config=config)

#     scheduler.run_all_trials()

#     logging.info("\nTHAT'S ALL FOR NOW FOLKS! THIS SHIT TOOK: %d", time.time() - start)


# if __name__ == "__main__":
#     main()
