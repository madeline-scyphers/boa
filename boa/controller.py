"""
###################################
Controller
###################################

The Controller class controls the optimization.

"""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Type

import yaml
from ax import Experiment

from boa.ax_instantiation_utils import get_experiment, get_scheduler
from boa.definitions import PathLike
from boa.logger import get_logger
from boa.runner import WrappedJobRunner
from boa.scheduler import Scheduler
from boa.storage import scheduler_from_json_file
from boa.wrappers.base_wrapper import BaseWrapper
from boa.wrappers.wrapper_utils import get_dt_now_as_str, initialize_wrapper

HEADER_BAR = """
##############################################
"""
LOG_INFO = """BOA Experiment Run
Output Experiment Dir: {exp_dir}
Start Time {start_time}"""


class Controller:
    """
    Controls the instantiation of your :class:`.BaseWrapper` and the
    necessary Ax objects to start your Experiment and control
    the BOA scheduler. Once the Controller sets up your Experiment, it starts
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

    def __init__(
        self,
        wrapper: Type[BaseWrapper] | BaseWrapper | PathLike,
        config_path: PathLike = None,
        config: dict = None,
        **kwargs,
    ):
        if not (config or config_path or isinstance(wrapper, BaseWrapper)):
            raise TypeError("Controller __init__() requires either config_path or config or an instantiated wrapper")
        if not isinstance(wrapper, BaseWrapper):
            wrapper = self.initialize_wrapper(wrapper=wrapper, config=config, config_path=config_path, **kwargs)

        if config_path:
            # Copy the experiment config to the experiment directory
            shutil.copyfile(wrapper.config_path, wrapper.experiment_dir / Path(config_path).name)
        else:
            with open(wrapper.experiment_dir / "config.yaml", "w") as f:
                # Write out config as yaml since we don't know what file format it came from
                yaml.dump(wrapper.config, f)
        self.wrapper = wrapper
        self.config = self.wrapper.config

        self.logger = self.start_logger()

        self.experiment: Experiment = None
        self.scheduler: Scheduler = None

    @classmethod
    def from_scheduler_path(cls, scheduler_path, wrapper: BaseWrapper | Type[BaseWrapper] | PathLike = None, **kwargs):
        if wrapper:
            wrapper = cls.initialize_wrapper(wrapper, **kwargs)
            scheduler = scheduler_from_json_file(scheduler_path, wrapper=wrapper)
        else:
            scheduler = scheduler_from_json_file(scheduler_path, **kwargs)
            wrapper = scheduler.experiment.runner.wrapper
            if "config_path" in kwargs:
                config = wrapper.load_config(kwargs["config_path"])
                wrapper.config = config

        inst = cls(wrapper=wrapper, **kwargs)
        inst.scheduler = scheduler
        inst.experiment = scheduler.experiment
        return inst

    @staticmethod
    def initialize_wrapper(*args, **kwargs):
        return initialize_wrapper(*args, **kwargs)

    def start_logger(self):
        self.logger = get_logger(filename=str(Path(self.wrapper.experiment_dir) / "optimization.log"))
        # setup file handler on ax logger too
        get_logger("ax", filename=str(Path(self.wrapper.experiment_dir) / "optimization.log"))
        return self.logger

    def initialize_scheduler(self, **kwargs) -> tuple[Scheduler, BaseWrapper]:
        """
        Sets experiment and scheduler

        Parameters
        ----------
        kwargs
            kwargs to pass to get_experiment and get_scheduler

        Returns
        -------
        returns a tuple with the first element being the scheduler
        and the second element being your wrapper (both initialized
        and ready to go)
        """

        self.experiment = get_experiment(self.config, WrappedJobRunner(wrapper=self.wrapper), self.wrapper, **kwargs)
        self.scheduler = get_scheduler(self.experiment, config=self.config, **kwargs)
        return self.scheduler, self.wrapper

    def run(self, scheduler: Scheduler = None, wrapper: BaseWrapper = None) -> Scheduler:
        """
        Run trials for scheduler

        Parameters
        ----------
        scheduler
            initialed scheduler or None, if None, defaults to
            ``self.scheduler`` (the scheduler set up in :meth:`.Controller.initialize_scheduler`
        wrapper
            initialed wrapper or None, if None, defaults to
            ``self.wrapper`` (the wrapper set up in :meth:`.Controller.initialize_wrapper`

        Returns
        -------
        The scheduler after all trials have been run or the
        experiment has been stopped for another reason.
        """
        start = time.time()
        start_tm = get_dt_now_as_str()
        self.logger.info(
            f"\n{HEADER_BAR}"
            f"\n\n{LOG_INFO.format(exp_dir=self.wrapper.experiment_dir, start_time=start_tm)}"
            f"\n{HEADER_BAR}"
        )

        scheduler = scheduler or self.scheduler
        wrapper = wrapper or self.wrapper
        if not scheduler or not wrapper:
            raise ValueError("Scheduler and wrapper must be defined, or setup in setup method!")

        try:
            final_msg = "Trials Completed!"
            scheduler.run_all_trials()
        except BaseException as e:
            final_msg = f"Error Completing because of {repr(e)}"
            raise
        finally:
            self.logger.info(
                f"\n{HEADER_BAR}"
                f"\n{final_msg}"
                f"\n{LOG_INFO.format(exp_dir=self.wrapper.experiment_dir, start_time=start_tm)}"
                f"\nEnd Time: {get_dt_now_as_str()}"
                f"\nTotal Run Time: {time.time() - start}"
                f"\n{HEADER_BAR}"
            )
        return scheduler
