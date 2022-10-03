import datetime as dt
import logging
import time
from pathlib import Path

from boa.ax_instantiation_utils import get_experiment, get_scheduler
from boa.runner import WrappedJobRunner
from boa.storage import scheduler_to_json_file
from boa.utils import get_dictionary_from_callable


class Controller:
    def __init__(self, config_path, wrapper):
        self.config_path = config_path
        self.wrapper = wrapper

        self.config = None

    def run(self, append_timestamp, experiment_dir, **kwargs):
        start = time.time()

        kwargs["config_path"] = self.config_path
        if experiment_dir:
            kwargs["experiment_dir"] = experiment_dir
        if append_timestamp is not None:
            kwargs["append_timestamp"] = append_timestamp

        load_config_kwargs = get_dictionary_from_callable(self.wrapper.load_config, kwargs)
        wrapper = self.wrapper(**load_config_kwargs)
        config = wrapper.config

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
        try:
            experiment_dir = wrapper.experiment_dir
            scheduler_to_json_file(scheduler, experiment_dir / "scheduler.json")
        except Exception as e:
            logging.exception("failed to save scheduler to json! Reason: %s" % repr(e))
        return scheduler
