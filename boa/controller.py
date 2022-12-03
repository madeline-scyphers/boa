"""
###################################
Controller
###################################

The Controller class controls the optimization.

"""
from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Type

from ax import Experiment
from ax.service.scheduler import Scheduler

from boa.ax_instantiation_utils import get_experiment, get_scheduler
from boa.logger import get_formatter, get_logger
from boa.runner import WrappedJobRunner
from boa.storage import scheduler_to_json_file
from boa.utils import get_dictionary_from_callable
from boa.wrappers.base_wrapper import BaseWrapper
from boa.wrappers.wrapper_utils import get_dt_now_as_str


class Controller:
    """
    Controls the instantiation of your :class:`.BaseWrapper` and the
    necessary Ax objects to start your Experiment and control
    the Ax scheduler. Once the Controller sets up your Experiment, it starts
    the scheduler, which runs your trials. It then
    saves the scheduler to a json file.

    Parameters
    ----------
    config_path
        Path to configuration yaml or json file
    wrapper
        Your Wrapper subclass of BaseWrapper to be instantiated

    See Also
    --------
    :ref:`Creating a configuration File`

    """

    def __init__(self, wrapper: Type[BaseWrapper], config_path: os.PathLike | str = None, config: dict = None):
        self.config_path = config_path
        self.config = config
        if not (self.config or self.config_path):
            raise TypeError("Controller __init__() requires either config_path or config")
        self.wrapper = wrapper

        self.experiment: Experiment = None
        self.scheduler: Scheduler = None

    def setup(
        self, append_timestamp: bool = None, experiment_dir: os.PathLike = None, **kwargs
    ) -> tuple[Scheduler, BaseWrapper]:
        """
        Sets up all the classes and objects needed to create the Ax Scheduler

        Parameters
        ----------
        append_timestamp
            Whether to append the output experiment directory with a timestamp or not
            (default True)
        experiment_dir
            Output experiment directory to which the experiment and trials will be saved
            (defaults to experiment_dir specified in the config script options
            or working_dir/experiment_name [if working_dir specified in config]
            or current_dir/experiment_name [if working_dir and experiment_dir and
            not specified])

        Returns
        -------
        returns a tuple with the first element being the scheduler
        and the second element being your wrapper (both initialized
        and ready to go)
        """
        if self.config:
            kwargs["config"] = self.config
        if self.config_path:
            kwargs["config_path"] = self.config_path
        if experiment_dir:
            kwargs["experiment_dir"] = experiment_dir
        if append_timestamp is not None:
            kwargs["append_timestamp"] = append_timestamp

        load_config_kwargs = get_dictionary_from_callable(self.wrapper.__init__, kwargs)
        self.wrapper: BaseWrapper = self.wrapper(**load_config_kwargs)
        config = self.wrapper.config

        logger = get_logger(__name__)
        fh = logging.FileHandler(str(Path(self.wrapper.experiment_dir) / "optimization.log"))
        formatter = get_formatter()
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        logger.info("Start time: %s", get_dt_now_as_str())

        self.experiment = get_experiment(config, WrappedJobRunner(wrapper=self.wrapper), self.wrapper)
        self.scheduler = get_scheduler(self.experiment, config=config)
        return self.scheduler, self.wrapper

    def run(self, scheduler: Scheduler = None, wrapper: BaseWrapper = None) -> Scheduler:
        """
        Run trials for scheduler

        Parameters
        ----------
        scheduler
            initialed scheduler or None, if None, defaults to
            ``self.scheduler`` (the scheduler set up in :meth:`.Controller.setup`
        wrapper
            initialed wrapper or None, if None, defaults to
            ``self.wrapper`` (the wrapper set up in :meth:`.Controller.setup`

        Returns
        -------
        The scheduler after all trials have been run or the
        experiment has been stopped for another reason.
        """
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
