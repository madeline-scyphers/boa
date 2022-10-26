"""
###################################
Controller
###################################

"""


import logging
import os
import time
from pathlib import Path

from ax.service.scheduler import Scheduler

from boa.ax_instantiation_utils import get_experiment, get_scheduler
from boa.runner import WrappedJobRunner
from boa.storage import scheduler_to_json_file
from boa.utils import get_dictionary_from_callable
from boa.wrappers.wrapper import BaseWrapper
from boa.wrappers.wrapper_utils import get_dt_now_as_str


class Controller:
    def __init__(self, config_path, wrapper):
        self.config_path = config_path
        self.wrapper = wrapper

        self.config = None

        self.scheduler = None

    def setup(self, append_timestamp: bool = None, experiment_dir: os.PathLike = None, **kwargs):
        kwargs["config_path"] = self.config_path
        if experiment_dir:
            kwargs["experiment_dir"] = experiment_dir
        if append_timestamp is not None:
            kwargs["append_timestamp"] = append_timestamp

        load_config_kwargs = get_dictionary_from_callable(self.wrapper.load_config, kwargs)
        self.wrapper = self.wrapper(**load_config_kwargs)
        config = self.wrapper.config

        log_format = "%(levelname)s %(asctime)s - %(message)s"
        logging.basicConfig(
            filename=Path(self.wrapper.experiment_dir) / "optimization.log",
            filemode="w",
            format=log_format,
            level=logging.DEBUG,
        )
        logging.getLogger().addHandler(logging.StreamHandler())
        logger = logging.getLogger(__file__)
        logger.info("Start time: %s", get_dt_now_as_str())

        experiment = get_experiment(config, WrappedJobRunner(wrapper=self.wrapper), self.wrapper)
        self.scheduler = get_scheduler(experiment, config=config)
        return self.scheduler

    def run(self, scheduler: Scheduler = None, wrapper: BaseWrapper = None):
        start = time.time()

        scheduler = scheduler or self.scheduler
        wrapper = wrapper or self.wrapper
        if not scheduler or not wrapper:
            raise ValueError("Scheduler and wrapper must be defined, or setup in setup method!")

        try:
            scheduler.run_all_trials()
        finally:
            logging.info("\nTrials completed! Total run time: %d", time.time() - start)
        try:
            experiment_dir = wrapper.experiment_dir
            scheduler_to_json_file(scheduler, experiment_dir / "scheduler.json")
        except Exception as e:
            logging.exception("failed to save scheduler to json! Reason: %s" % repr(e))
        return scheduler
