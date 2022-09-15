import datetime as dt
import logging
import time
from pathlib import Path

from boa.ax_instantiation_utils import get_experiment, get_scheduler
from boa.runner import WrappedJobRunner
from boa.utils import get_dictionary_from_callable


class Controller:
    def __init__(self, config_path, wrapper):
        self.config_path = config_path
        self.wrapper = wrapper

        self.config = None

    def run(self, append_timestamp):
        start = time.time()

        wrapper = self.wrapper()
        load_config_kwargs = get_dictionary_from_callable(
            wrapper.load_config, dict(config_path=self.config_path, append_timestamp=append_timestamp)
        )
        config = wrapper.load_config(**load_config_kwargs)

        log_format = "%(levelname)s %(asctime)s - %(message)s"
        logging.basicConfig(
            filename=Path(wrapper.experiment_dir) / "optimization.log",
            filemode="w",
            format=log_format,
            level=logging.DEBUG,
        )
        logging.getLogger().addHandler(logging.StreamHandler())
        logger = logging.getLogger(__file__)
        logger.info("Start time: %s", dt.datetime.now().strftime("%Y%m%dT%H%M%S"))

        experiment = get_experiment(config, WrappedJobRunner(wrapper=wrapper), wrapper)
        scheduler = get_scheduler(experiment, config=config)

        try:
            scheduler.run_all_trials()
        finally:
            logging.info("\nTrials completed! Total run time: %d", time.time() - start)
        return scheduler
