from __future__ import annotations

import pathlib
from pprint import pformat
from typing import Iterable, Optional

from ax.core.optimization_config import OptimizationConfig
from ax.modelbridge.base import ModelBridge
from ax.service.scheduler import Scheduler as AxScheduler

from boa.definitions import PathLike
from boa.logger import get_logger
from boa.runner import WrappedJobRunner
from boa.wrappers.base_wrapper import BaseWrapper

logger = get_logger()


class Scheduler(AxScheduler):
    runner: WrappedJobRunner

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._model: Optional[ModelBridge] = None
        self._scheduler_filepath: pathlib.Path = pathlib.Path("scheduler.json")
        self._opt_csv: pathlib.Path = pathlib.Path("optimization.csv")

    @property
    def wrapper(self) -> BaseWrapper:
        return self.runner.wrapper

    @property
    def model(self):
        return self._model or self.generation_strategy.model

    @model.setter
    def model(self, model):
        self._model = model

    @property
    def scheduler_filepath(self) -> pathlib.Path:
        return self.wrapper.experiment_dir / self._scheduler_filepath

    @scheduler_filepath.setter
    def scheduler_filepath(self, path: PathLike):
        self._scheduler_filepath = pathlib.Path(path)

    @property
    def opt_csv(self) -> pathlib.Path:
        return self.wrapper.experiment_dir / self._opt_csv

    @opt_csv.setter
    def opt_csv(self, path: PathLike):
        self._opt_csv = pathlib.Path(path)

    def report_results(self, force_refit: bool = False):
        """
        Ran whenever a batch of data comes in and the results are ready. This could be
        from one trial or a group of trials at once since it does interval polls to check
        trial statuses.

        saves the scheduler to json and saves to the log a status update of what trials
        have finished, which are running, and what generation step will be used to
        generate the next trials.

        Args:
            force_refit: Not used. Arg from Ax for compatibility.
        """
        self.save_data()
        try:
            trials = self.best_raw_trials()
            best_trial_map = {idx: trial_dict["means"] for idx, trial_dict in trials.items()} if trials else {}
            best_trial_str = f"\nBest trial so far: {pformat(best_trial_map)}"
        except Exception as e:  # pragma: no cover
            best_trial_str = ""
            logger.exception(e)
        trials_ls = [str(t.index) for t in self.running_trials]
        if len(trials_ls) == 1:
            trials_ls = trials_ls[0]
        update = (
            f"Trials so far: {len(self.experiment.trials)}"
            f"\nCurrently running trials: {trials_ls}"
            f"\nWill Produce next trials from generation step: {self.generation_strategy.current_step.model_name}"
            f"{best_trial_str}"
        )
        logger.info(update)

    def best_fitted_trials(
        self,
        optimization_config: Optional[OptimizationConfig] = None,
        trial_indices: Optional[Iterable[int]] = None,
        use_model_predictions: bool = True,
        *args,
        **kwargs,
    ) -> dict:
        """Identifies and fit the best parameterizations tried in the experiment so far,
        this model predictions (fitting) if ``use_model_predictions`` is true and using
        observed raw values from the experiment otherwise. By default, uses model
        predictions to account for observation noise.

        If it is a Multi Objective Problem, then it will return the pareto front, a collection
        of trials that are the best front that min/maxes the objectives. Else it is
        the best point that min/maxes the objective.

        NOTE: The format of this method's output is as follows:
        { trial_index: {params: best parameters, means: dict of metrics by nam, cov_matrix: dict of cov matrix} },

        Args:
            optimization_config: Optimization config to use in place of the one stored
                on the experiment.
            trial_indices: Indices of trials for which to retrieve data. If None will
                retrieve data from all available trials.
            use_model_predictions: Whether to extract the Pareto frontier using
                model predictions or directly observed values. If ``True``,
                the metric means and covariances in this method's output will
                also be based on model predictions and may differ from the
                observed values.

        Returns:
            ``None`` if it was not possible to extract the best trial
            or best Pareto frontier,
            otherwise a mapping from trial index to the tuple of:
            - the parameterization of the arm in that trial,
            - two-item tuple of metric means dictionary and covariance matrix
            (model-predicted if ``use_model_predictions=True`` and observed
            otherwise).
        """
        trials = None
        if self.experiment.is_moo_problem:
            try:
                trials = self.get_pareto_optimal_parameters(
                    optimization_config=optimization_config,
                    trial_indices=trial_indices,
                    use_model_predictions=use_model_predictions,
                    *args,
                    **kwargs,
                )
                if trials:
                    trials = {
                        idx: dict(params=trial_tup[0], means=trial_tup[1][0], cov_matrix=trial_tup[1][1])
                        for idx, trial_tup in trials.items()
                    }
            except (TypeError, ValueError) as e:  # pragma: no cover
                # If get_pareto doesn't work because of the gen_step not supporting multi obj
                # then we log to the user that problem
                logger.warning(
                    "Problem generating best fitted trials for pareto frontier. most likely cause"
                    " is the generation step model/acquisition function is not intended for"
                    f" multi objective optimizations. Exception: {e!r}"
                )

        else:
            trials = self.get_best_trial(
                optimization_config=optimization_config,
                trial_indices=trial_indices,
                use_model_predictions=use_model_predictions,
                *args,
                **kwargs,
            )
            if trials:
                best_trial, best_params, (means_dict, cov_matrix) = self.get_best_trial(
                    optimization_config=optimization_config,
                    trial_indices=trial_indices,
                    use_model_predictions=use_model_predictions,
                    *args,
                    **kwargs,
                )
                trials = {int(best_trial): dict(params=best_params, means=means_dict, cov_matrix=cov_matrix)}
        return trials

    def best_raw_trials(
        self,
        optimization_config: Optional[OptimizationConfig] = None,
        trial_indices: Optional[Iterable[int]] = None,
        use_model_predictions: bool = False,
        *args,
        **kwargs,
    ) -> dict:
        """Identifies the best parameterizations tried in the experiment so far
        using the raw points themselves.

        If it is a Multi Objective Problem, then it will return the pareto front, a collection
        of trials that are the best front that min/maxes the objectives. Else it is
        the best point that min/maxes the objective.

        NOTE: The format of this method's output is as follows:
        { trial_index: {params: best parameters, means: dict of metrics by nam, cov_matrix: dict of cov matrix} },

        Args:
            optimization_config: Optimization config to use in place of the one stored
                on the experiment.
            trial_indices: Indices of trials for which to retrieve data. If None will
                retrieve data from all available trials.
            use_model_predictions: Whether to extract the Pareto frontier using
                model predictions or directly observed values. If ``True``,
                the metric means and covariances in this method's output will
                also be based on model predictions and may differ from the
                observed values.

        Returns:
            ``None`` if it was not possible to extract the best trial
            or best Pareto frontier,
            otherwise a mapping from trial index to the tuple of:
            - the parameterization of the arm in that trial,
            - two-item tuple of metric means dictionary and covariance matrix
            (model-predicted if ``use_model_predictions=True`` and observed
            otherwise).
        """
        trials = None
        if self.experiment.is_moo_problem:
            try:
                trials = self.get_pareto_optimal_parameters(
                    optimization_config=optimization_config,
                    trial_indices=trial_indices,
                    use_model_predictions=use_model_predictions,
                    *args,
                    **kwargs,
                )
                if trials:
                    trials = {
                        idx: dict(params=trial_tup[0], means=trial_tup[1][0], cov_matrix=trial_tup[1][1])
                        for idx, trial_tup in trials.items()
                    }
            except (TypeError, ValueError) as e:  # pragma: no cover
                # If get_pareto doesn't work because of the gen_step not supporting multi obj
                # then we log to the user that problem
                logger.warning(
                    "Problem generating best fitted trials for pareto frontier. most likely cause"
                    " is the generation step model/acquisition function is not intended for"
                    f" multi objective optimizations. Exception: {e!r}"
                )

        else:
            trials = self.get_best_trial(
                optimization_config=optimization_config,
                trial_indices=trial_indices,
                use_model_predictions=use_model_predictions,
                *args,
                **kwargs,
            )
            if trials:
                best_trial, best_params, (means_dict, cov_matrix) = self.get_best_trial(
                    optimization_config=optimization_config,
                    trial_indices=trial_indices,
                    use_model_predictions=use_model_predictions,
                    *args,
                    **kwargs,
                )
                trials = {int(best_trial): dict(params=best_params, means=means_dict, cov_matrix=cov_matrix)}
        return trials

    def save_data(self, **kwargs):
        """Save Scheduler to json file. Defaults to `wrapper.experiment_dir` / `filepath`"""
        from boa.storage import dump_scheduler_data

        try:
            dump_scheduler_data(
                scheduler=self,
                dir_=self.runner.wrapper.experiment_dir,
                scheduler_filepath=self.scheduler_filepath,
                opt_filepath=self.opt_csv,
                **kwargs,
            )
        except Exception as e:
            logger.exception("failed to save scheduler to json! Reason: %s" % repr(e))
