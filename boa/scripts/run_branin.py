import logging
import shutil
import time
from pathlib import Path

from ax.service.utils.report_utils import exp_to_df

try:
    from script_wrappers import Wrapper  # pragma: no cover
except ImportError:
    from .script_wrappers import Wrapper

from boa import (
    BOAConfig,
    WrappedJobRunner,
    get_dt_now_as_str,
    get_experiment,
    get_scheduler,
)
from boa.logger import get_logger


def main():
    # with tempfile.TemporaryDirectory() as exp_dir:
    exp_dir = "."
    return run_opt(exp_dir)


def run_opt(exp_dir):
    config_file = Path(__file__).parent / "synth_func_config.yaml"
    start = time.time()
    wrapper = Wrapper(config_path=config_file, experiment_dir=exp_dir)
    config: BOAConfig = wrapper.config
    experiment_dir = wrapper.experiment_dir
    # Copy the experiment config to the experiment directory
    shutil.copyfile(config_file, experiment_dir / Path(config_file).name)
    logger = get_logger(filename=str(Path(wrapper.experiment_dir) / "optimization.log"))
    logger.info("Start time: %s", get_dt_now_as_str())

    experiment = get_experiment(config, WrappedJobRunner(wrapper=wrapper), wrapper)
    scheduler = get_scheduler(experiment, config=config)
    total_trials = config.scheduler.total_trials
    # we leave some trials off for use in unit tests
    scheduler.run_n_trials(total_trials - 5)

    # We output a bunch of stuff to the log for easier debugging
    logger.info(scheduler.experiment.fetch_data().df)
    logging.info(exp_to_df(scheduler.experiment))

    logger.info("\nTrials completed! Total run time: %d", time.time() - start)
    return scheduler


if __name__ == "__main__":
    main()
