import datetime as dt
import logging
import shutil
import tempfile
import time
from pathlib import Path

import click
from ax.service.utils.report_utils import exp_to_df

try:
    from script_wrappers import Wrapper
except ImportError:
    from .script_wrappers import Wrapper

from boa import WrappedJobRunner, get_experiment, get_scheduler, get_dt_now_as_str
from boa.logger import get_logger, get_formatter


@click.command()
@click.option("-o", "--output_dir", type=click.Path(), default="")
def main(output_dir):
    if output_dir:
        return run_opt(output_dir)
    with tempfile.TemporaryDirectory() as output_dir:
        return run_opt(output_dir)


def run_opt(output_dir):
    config_file = Path(__file__).parent / "synth_func_config.yaml"
    start = time.time()
    wrapper = Wrapper(config_path=config_file, working_dir=output_dir)
    config = wrapper.config
    experiment_dir = wrapper.experiment_dir
    # Copy the experiment config to the experiment directory
    shutil.copyfile(config_file, experiment_dir / Path(config_file).name)
    logger = get_logger(__name__)
    fh = logging.FileHandler(str(Path(wrapper.experiment_dir) / "optimization.log"))
    formatter = get_formatter()
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    logger.info("Start time: %s", get_dt_now_as_str())

    experiment = get_experiment(config, WrappedJobRunner(wrapper=wrapper), wrapper)
    scheduler = get_scheduler(experiment, config=config)
    total_trials = config["optimization_options"]["scheduler"]["total_trials"]
    # we leave some trials off for use in unit tests
    scheduler.run_n_trials(total_trials - 5)

    # We output a bunch of stuff to the log for easier debugging
    logger.info(scheduler.experiment.fetch_data().df)
    logging.info(exp_to_df(scheduler.experiment))

    logger.info("\nTrials completed! Total run time: %d", time.time() - start)
    return scheduler, config


if __name__ == "__main__":
    main()
