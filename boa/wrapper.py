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
        pass

    def run_model(self, trial: BaseTrial) -> None:
        """
        Runs a model by deploying a given trial.

        Parameters
        ----------
        trial : BaseTrial
        """

    def set_trial_status(self, trial: BaseTrial) -> None:
        """
        The trial gets polled from time to time to see if it is completed, failed, still running,
        etc. This marks the trial as one of those options based on some criteria of the model.
        If the model is still running, don't do anything with the trial.

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
        function. The return value needs to be a dictionary with the keys matching the keys
        of the metric function used in the objective function.
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

    def wrapper_to_dict(self) -> dict:
        """Convert Ax experiment to a dictionary."""
        parents = self.__class__.mro()[1:]  # index 0 is the class itself

        wrapper_state = serialize_init_args(self, parents=parents, match_private=True)

        wrapper_state = convert_type(wrapper_state, {Path: str})
        return {"__type": self.__class__.__name__, **wrapper_state}
