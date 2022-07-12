from __future__ import annotations

import os
from pathlib import Path

from ax.core.base_trial import BaseTrial

from boa.metaclasses import WrapperRegister
from boa.utils import convert_type, serialize_init_args


class BaseWrapper(metaclass=WrapperRegister):
    def load_config(self, config_file: os.PathLike):
        """
        Load config file and return a dictionary # TODO finish this

        Parameters
        ----------
        config_file : os.PathLike
            File path for the experiment configuration file

        Returns
        -------
        loaded_config: dict
        """

    def write_configs(self, trial: BaseTrial) -> None:
        """

        Parameters
        ----------
        trial :

        Returns
        -------

        """

    def run_model(self, trial: BaseTrial) -> None:
        """
        Runs a model by deploying a given trial.

        Parameters
        ----------
        trial : BaseTrial
        """

    def set_trial_status(self, trial: BaseTrial) -> None:
        """
        Marks the status of a trial to reflect the status of the model run for the trial.

        Each trial will be polled periodically to determine its status (completed, failed, still running,
        etc). This function defines the criteria for determining the status of the model run for a trial (e.g., whether
        the model run is completed/still running, failed, etc). The trial status is updated accordingly when the trial
        is polled.

        The approach for determining the trial status will depend on the structure of the particular model and its
        outputs. One example is checking the log files of the model.

        .. todo::
            Add examples/links of different approaches

        Parameters
        ----------
        trial : BaseTrial

        Examples
        --------
        trial.mark_completed()
        trial.mark_failed()
        trial.mark_abandoned()
        trial.mark_early_stopped()

        See Also
        --------
        # TODO add sphinx link to ax trial status
        """

    def fetch_trial_data(
        self, trial: BaseTrial, metric_properties: dict, metric_name: str, *args, **kwargs
    ) -> dict:
        """
        Retrieves the trial data and prepares it for the metric(s) used in the objective
        function.

        For example, for a case where you are minimizing the error between a model and observations, using RMSE as a
        metric, this function would load the model output and the corresponding observation data that will be passed to
        the RMSE metric.

        The return value of this function is a dictionary, with keys that match the keys
        of the metric used in the objective function.
        # TODO work on this description

        Parameters
        ----------
        trial : BaseTrial
        metric_properties: dict
        metric_name: str

        Returns
        -------
        dict
            A dictionary with the keys matching the keys of the metric function
                used in the objective
        """

    # TODO remove this method
    # def wrapper_to_dict(self) -> dict:
    #     """Convert Ax experiment to a dictionary.
    #     """
    #     parents = self.__class__.mro()[1:]  # index 0 is the class itself
    #
    #     wrapper_state = serialize_init_args(self, parents=parents, match_private=True)
    #
    #     wrapper_state = convert_type(wrapper_state, {Path: str})
    #     return {"__type": self.__class__.__name__, **wrapper_state}
