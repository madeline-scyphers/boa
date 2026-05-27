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

from boa.__version__ import __version__ as VERSION
from boa.client import BOAClient, get_client
from boa.config import BOAConfig
from boa.definitions import PathLike
from boa.logger import get_logger
from boa.utils import yaml_dump
from boa.wrappers.base_wrapper import BaseWrapper
from boa.wrappers.wrapper_utils import get_dt_now_as_str, initialize_wrapper

HEADER_BAR = """
##############################################
"""
LOG_INFO = (
    """BOA Experiment Run
Output Experiment Dir: {exp_dir}
Client File Path: {client_path}
Optimization CSV File Path: {opt_csv_path}
Start Time: {start_time}
Version: """
    + f"{VERSION}"
)


class Controller:
    """
    Controls the instantiation of your :class:`.BaseWrapper` and the
    necessary Ax objects to start your experiment and control
    the BOA client. Once the Controller sets up your experiment, it starts
    the client, which runs your trials. It then saves the client to a json file.

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
        config: BOAConfig = None,
        **kwargs,
    ):
        if not (config or config_path or isinstance(wrapper, BaseWrapper)):
            raise TypeError("Controller __init__() requires either config_path or config or an instantiated wrapper")
        if not isinstance(wrapper, BaseWrapper):
            wrapper = self.initialize_wrapper(wrapper=wrapper, config=config, config_path=config_path, **kwargs)

        if config_path:
            # Copy the experiment config to the experiment directory
            shutil.copyfile(config_path, wrapper.experiment_dir / Path(config_path).name)
        else:
            if wrapper.config.orig_config:
                d = wrapper.config.orig_config
            else:
                d = wrapper.config.to_dict()
            yaml_dump(d, wrapper.experiment_dir / "config.yaml")

        self.wrapper = wrapper
        self.config = self.wrapper.config

        self.logger = self.start_logger()

        self.client: BOAClient = None

    @classmethod
    def from_client(cls, client, working_dir=None, **kwargs):
        wrapper = client.wrapper or kwargs.pop("wrapper", None)
        if wrapper is None:
            raise ValueError("Loaded client does not have a BOA wrapper attached. Pass an instantiated wrapper.")

        inst = cls(wrapper=wrapper, working_dir=working_dir, **kwargs)
        if inst.wrapper.config_path:
            inst.logger.info(f"Config path: {inst.wrapper.config_path}")

        inst.client = client
        return inst

    @staticmethod
    def initialize_wrapper(*args, **kwargs):
        return initialize_wrapper(*args, **kwargs)

    def start_logger(self):
        self.logger = get_logger(filename=str(Path(self.wrapper.experiment_dir) / "optimization.log"))
        # setup file handler on ax logger too
        get_logger("ax", filename=str(Path(self.wrapper.experiment_dir) / "optimization.log"))
        return self.logger

    def initialize_client(self, **kwargs) -> tuple[BOAClient, BaseWrapper]:
        """
        Sets and configures the BOA client.

        Returns
        -------
        returns a tuple with the first element being the client
        and the second element being your wrapper (both initialized
        and ready to go)
        """
        self.client = get_client(config=self.config, wrapper=self.wrapper, **kwargs)
        return self.client, self.wrapper

    def run(self, client: BOAClient = None, wrapper: BaseWrapper = None) -> BOAClient:
        """
        Run trials for client

        Parameters
        ----------
        client
            initialized client or None, if None, defaults to
            ``self.client`` (the client set up in :meth:`.Controller.initialize_client`)
        wrapper
            initialed wrapper or None, if None, defaults to
            ``self.wrapper`` (the wrapper set up in :meth:`.Controller.initialize_wrapper`

        Returns
        -------
        The client after all trials have been run or the
        experiment has been stopped for another reason.
        """
        start = time.time()
        start_tm = get_dt_now_as_str()
        client = client or self.client
        wrapper = wrapper or self.wrapper
        self.logger.info(
            f"\n{HEADER_BAR}"
            f"""\n\n{LOG_INFO.format(
                exp_dir=wrapper.experiment_dir,
                start_time=start_tm,
                client_path=client.client_filepath,
                opt_csv_path=client.optimization_csv)}"""
            f"\n{HEADER_BAR}"
        )

        if not client or not wrapper:
            raise ValueError("Client and wrapper must be defined, or setup in setup method!")

        try:
            final_msg = "Trials Completed!"
            if self.config.n_trials:
                client.run_trials(max_trials=self.config.n_trials)
            else:
                client.run_trials()
        except BaseException as e:
            final_msg = f"Error Completing because of {repr(e)}"
            raise
        finally:
            client.save_data()
            self.logger.info(
                f"\n{HEADER_BAR}"
                f"\n{final_msg}"
                f"""\n{LOG_INFO.format(
                    exp_dir=self.wrapper.experiment_dir,
                    start_time=start_tm,
                    client_path=client.client_filepath,
                    opt_csv_path=client.optimization_csv)}"""
                f"\nEnd Time: {get_dt_now_as_str()}"
                f"\nTotal Run Time: {time.time() - start}"
                "\n"
                f"\n{client.summarize()}"
                f"\n{HEADER_BAR}"
            )
        return client