"""
###################################
Wrapped Runner
###################################

Runner that calls your :mod:`.wrappers` to run your model and poll the trial status.

"""

import concurrent.futures
import logging
from collections import defaultdict
from typing import Any, Dict, Iterable, Set

from ax.core.base_trial import TrialStatus
from ax.core.runner import Runner
from ax.core.trial import Trial

from boa.logger import get_logger, queue
from boa.metaclasses import RunnerRegister
from boa.utils import serialize_init_args
from boa.wrappers.base_wrapper import BaseWrapper

logger = get_logger()


class WrappedJobRunner(Runner, metaclass=RunnerRegister):
    def __init__(self, wrapper: BaseWrapper = None, *args, **kwargs):

        self.wrapper = wrapper or BaseWrapper()
        super().__init__(*args, **kwargs)

    def run(self, trial: Trial) -> Dict[str, Any]:
        """Deploys a trial based on custom runner subclass implementation.

        Args:
            trial: The trial to deploy.

        Returns:
            Dict of run metadata from the deployment process.
        """
        qh = logging.handlers.QueueHandler(queue)
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(qh)

        if not isinstance(trial, Trial):
            raise ValueError("This runner only handles `Trial`.")

        self.wrapper.write_configs(trial)

        self.wrapper.run_model(trial)
        # This run metadata will be attached to trial as `trial.run_metadata`
        # by the base `Scheduler`.
        return {"job_id": trial.index}

    def run_multiple(self, trials) -> Dict[int, Dict[str, Any]]:
        """Runs a single evaluation for each of the given trials. Useful when deploying
        multiple trials at once is more efficient than deploying them one-by-one.
        Used in Ax ``Scheduler``.

        NOTE: By default simply loops over `run_trial`. Should be overwritten
        if deploying multiple trials in batch is preferable.

        Args:
            trials: Iterable of trials to be deployed, each containing arms with
                parameterizations to be evaluated. Can be a `Trial`
                if contains only one arm or a `BatchTrial` if contains
                multiple arms.

        Returns:
            Dict of trial index to the run metadata of that trial from the deployment
            process.
        """
        results = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            trial_runs = {executor.submit(self.run, trial=trial): trial.index for trial in trials}
            for future in concurrent.futures.as_completed(trial_runs):
                trial_index = trial_runs[future]
                try:
                    results[trial_index] = future.result()
                except Exception as e:
                    logger.exception(f"Error completing run because of {e}!")
                    raise
            concurrent.futures.wait(trial_runs)

        return results

    def poll_trial_status(self, trials: Iterable[Trial]) -> Dict[TrialStatus, Set[int]]:
        """Checks the status of any non-terminal trials and returns their
        indices as a mapping from TrialStatus to a list of indices. Required
        for runners used with Ax ``Scheduler``.

        NOTE: Does not need to handle waiting between polling calls while trials
        are running; this function should just perform a single poll.

        Args:
            trials: Trials to poll.

        Returns:
            A dictionary mapping TrialStatus to a list of trial indices that have
            the respective status at the time of the polling. This does not need to
            include trials that at the time of polling already have a terminal
            (ABANDONED, FAILED, COMPLETED) status (but it may).
        """
        status_dict = defaultdict(set)
        for trial in trials:
            self.wrapper.set_trial_status(trial)
            status_dict[trial.status].add(trial.index)

        return status_dict

    def to_dict(self) -> dict:
        """Convert runner to a dictionary."""

        parents = self.__class__.mro()[1:]  # index 0 is the class itself

        properties = serialize_init_args(self, parents=parents, match_private=True, exclude_fields=["wrapper"])

        properties["__type"] = self.__class__.__name__
        return properties
