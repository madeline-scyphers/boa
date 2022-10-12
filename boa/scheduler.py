from __future__ import annotations

import logging
import os
from pprint import pformat
from typing import Iterable, Optional

from ax.core.optimization_config import OptimizationConfig
from ax.modelbridge.modelbridge_utils import observed_pareto_frontier as observed_pareto
from ax.modelbridge.registry import Models
from ax.service.scheduler import Scheduler as AxScheduler

from boa.runner import WrappedJobRunner
from boa.storage import scheduler_to_json_file

logger = logging.getLogger(__file__)


class Scheduler(AxScheduler):
    runner: WrappedJobRunner

    def report_results(self):
        """
        Ran whenever a batch of data comes in and the results are ready. This could be
        from one trial or a group of trials at once since it does interval polls to check
        trial statuses.

        saves the scheduler to json and saves to the log a status update of what trials
        have finished, which are running, and what generation step will be used to
        generate the next trials.
        """
        self.save_to_json()
        try:
            trials = self.best_fitted_trials(use_model_predictions=False)
            best_trial_map = {idx: trial_dict["means"] for idx, trial_dict in trials.items()} if trials else {}
            best_trial_str = f"\nBest trial so far: {pformat(best_trial_map)}"
        except Exception as e:
            best_trial_str = ""
            logger.exception(e)
        update = (
            f"Trials so far: {len(self.experiment.trials)}"
            f"\nRunning trials: {', '.join(str(t.index) for t in self.running_trials)}"
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
        """Identifies the best parameterizations tried in the experiment so far,
        using model predictions if ``use_model_predictions`` is true and using
        observed values from the experiment otherwise. By default, uses model
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
            except (TypeError, ValueError):
                # If get_pareto doesn't work because of the gen_step not supporting multi obj
                # then infer obj thresholds with generic MOO model
                modelbridge = Models.MOO(
                    experiment=self.experiment,
                    search_space=self.experiment.search_space,
                    data=self.experiment.lookup_data(),
                )
                ot = modelbridge.infer_objective_thresholds(
                    search_space=self.experiment.search_space,
                    optimization_config=self.experiment.optimization_config,
                    fixed_features=None,
                )
                oc = self.experiment.optimization_config.clone()
                oc.objective_thresholds = ot
                # Once we have inferred objective thresholds, get pareto front
                trials = observed_pareto(modelbridge=modelbridge, objective_thresholds=ot, optimization_config=oc)
                if trials:
                    trials = {
                        int(obs.features.trial_index): dict(
                            params=obs.features.parameters,
                            means=obs.data.means_dict,
                            cov_matrix=obs.data.covariance_matrix,
                        )
                        for obs in trials
                    }
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

    def save_to_json(self, filepath: os.PathLike = "scheduler.json"):
        """Save Scheduler to json file in `wrapper.experiment_dir`/`filepath`"""
        try:
            experiment_dir = self.runner.wrapper.experiment_dir
            scheduler_to_json_file(self, experiment_dir / filepath)
        except Exception as e:
            logger.exception("failed to save scheduler to json! Reason: %s" % repr(e))
