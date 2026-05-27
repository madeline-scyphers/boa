import logging
import tempfile
import time
from pathlib import Path

try:
    from script_wrappers import BraninWrapper  # pragma: no cover
except ImportError:
    from .script_wrappers import BraninWrapper

from boa import Controller, get_dt_now_as_str

from boa.logger import get_logger


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        experiment_dir = Path(temp_dir)
        return run_opt(exp_dir=experiment_dir)


def run_opt(exp_dir):
    config_file = Path(__file__).parent / "synth_func_config.yaml"
    start = time.time()
    wrapper = BraninWrapper(config_path=config_file, experiment_dir=exp_dir)
    experiment_dir = wrapper.experiment_dir
    logger = get_logger(filename=str(Path(wrapper.experiment_dir) / "optimization.log"))
    logger.info("Start time: %s", get_dt_now_as_str())

    controller = Controller(wrapper=wrapper, config_path=config_file)
    client, _ = controller.initialize_client()
    total_trials = wrapper.config.trials
    # we leave some trials off for use in unit tests
    client.run_trials(max_trials=total_trials - 5)
    client.save_data()

    # We output a bunch of stuff to the log for easier debugging
    logger.info(client.summarize())
    logging.info(client.summarize())

    logger.info("\nTrials completed! Total run time: %d", time.time() - start)
    return client


if __name__ == "__main__":
    main()