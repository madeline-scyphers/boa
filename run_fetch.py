import datetime as dt
import logging
import time
from pathlib import Path

import click
from ax.storage.json_store.save import save_experiment
from ax.storage.registry_bundle import RegistryBundle

from fetch_wrapper import Fetch3Wrapper
from optiwrap import (
    MSE,
    WrappedJobRunner,
    get_experiment,
    get_metric_from_config,
    get_scheduler,
    make_experiment_dir,
    load_experiment_config,
)


@click.command()
@click.option(
    "-f",
    "--config_file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    # default="/Users/madelinescyphers/projs/fetch3_nhl/optimize/opt_model_config.yml",
    default="/Users/madelinescyphers/projs/fetch3_nhl/optimize/optiwrap_config.yaml",
    help="Path to configuration YAML file.",
)
def main(config_file):
    """This is my docstring

    Args:
        config (os.PathLike): Path to configuration YAML file
    """
    start = time.time()

    config = load_experiment_config(config_file)  # Read experiment config'
    experiment_dir = make_experiment_dir(config["optimization_options"]["working_dir"],
                                         config["optimization_options"]["experiment_name"])

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
    )

    experiment = get_experiment(config, WrappedJobRunner(wrapper=wrapper), wrapper)

    scheduler = get_scheduler(experiment, config=config)

    scheduler.run_all_trials()

    metric = get_metric_from_config(config["optimization_options"]["metric"])
    bundle = RegistryBundle(
        metric_clss={metric: None},
        runner_clss={WrappedJobRunner: None}
    )
    save_experiment(experiment, "experiment.json", encoder_registry=bundle.encoder_registry)
    # from ax.storage.json_store.load import load_experiment
    logging.info("\nTrials completed! Total run time: %d", time.time() - start)


if __name__ == "__main__":
    main()
