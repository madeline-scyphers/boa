import logging
import os
from pprint import pformat

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
        if self.experiment.is_moo_problem:
            try:
                trials = self.get_pareto_optimal_parameters(use_model_predictions=False)
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
                pareto_optimal_observations = observed_pareto(
                    modelbridge=modelbridge, objective_thresholds=ot, optimization_config=oc
                )
                trials = {
                    int(obs.features.trial_index): (
                        obs.features.parameters,
                        (obs.data.means_dict, obs.data.covariance_matrix),
                    )
                    for obs in pareto_optimal_observations
                }

            # trial_tup[0] are params, trial_tup[1][1] is the cov matrix
            best_trial_map = {idx: trial_tup[1][0] for idx, trial_tup in trials.items()} if trials else {}
        else:
            best_trial, best_params, obj = self.get_best_trial(use_model_predictions=False)
            best_trial_map = {best_trial: obj[0]}
        update = (
            f"Trials so far: {len(self.experiment.trials)}"
            f"\nRunning trials: {', '.join(str(t.index) for t in self.running_trials)}"
            f"\nWill Produce next trials from generation step: {self.generation_strategy.current_step.model_name}"
            f"\nBest trial so far: {pformat(best_trial_map)}"
        )
        logger.info(update)

    def save_to_json(self, filepath: os.PathLike = "scheduler.json"):
        """Save Scheduler to json file in `wrapper.experiment_dir`/`filepath`"""
        try:
            experiment_dir = self.runner.wrapper.experiment_dir
            scheduler_to_json_file(self, experiment_dir / filepath)
        except Exception as e:
            logger.exception("failed to save scheduler to json! Reason: %s" % repr(e))
