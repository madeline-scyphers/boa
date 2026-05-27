from __future__ import annotations

import pathlib
from pprint import pformat
from typing import Iterable, Optional
from dataclasses import replace
from typing_extensions import deprecated

from boa.ax_api import Adapter, OptimizationConfig, Client, Orchestrator, OrchestratorOptions, TrialStatus, db_settings_from_storage_config
from boa.ax_api import Scheduler as AxScheduler
from boa.definitions import PathLike
from boa.logger import get_logger
from boa.runner import WrappedJobRunner
from boa.wrappers.base_wrapper import BaseWrapper

logger = get_logger()


class Scheduler(AxScheduler):
    runner: WrappedJobRunner

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._adapter: Optional[Adapter] = None
        self._scheduler_filepath: pathlib.Path = pathlib.Path("scheduler.json")
        self._opt_csv: pathlib.Path = pathlib.Path("optimization.csv")

    @property
    def wrapper(self) -> BaseWrapper:
        return self.runner.wrapper

    @property
    def adapter(self):
        return self._adapter or self.generation_strategy.adapter

    @adapter.setter
    def adapter(self, adapter):
        self._adapter = adapter

    @property
    @deprecated("model property is deprecated. Please use adapter instead.")
    def model(self):
        return self.adapter

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
            f"\nWill Produce next trials from node: {self.generation_strategy.current_node_name}"
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



class BOAClient(Client):
    """BOA's Ax >=1 client runtime.

    This class keeps Ax ``Client`` as the public optimization API while adding
    BOA-owned wrapper, persistence, reporting, and full ``OrchestratorOptions``
    support.
    """

    def __init__(
        self,
        *args,
        wrapper: Optional[BaseWrapper] = None,
        orchestrator_options: Optional[OrchestratorOptions] = None,
        client_filepath: PathLike = "client.json",
        optimization_csv: PathLike = "optimization.csv",
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.wrapper = wrapper
        self.orchestrator_options = orchestrator_options
        self._client_filepath = pathlib.Path(client_filepath)
        self._optimization_csv = pathlib.Path(optimization_csv)
        self._last_orchestrator: Orchestrator | None = None

    @property
    def experiment(self):
        return self._experiment

    @property
    def generation_strategy(self):
        return self._generation_strategy_or_choose()

    @property
    def client_filepath(self) -> pathlib.Path:
        return self._resolve_output_path(self._client_filepath)

    @client_filepath.setter
    def client_filepath(self, path: PathLike):
        self._client_filepath = pathlib.Path(path)

    @property
    def optimization_csv(self) -> pathlib.Path:
        return self._resolve_output_path(self._optimization_csv)

    @optimization_csv.setter
    def optimization_csv(self, path: PathLike):
        self._optimization_csv = pathlib.Path(path)

    @property
    def last_orchestrator(self) -> Orchestrator | None:
        return self._last_orchestrator

    def _resolve_output_path(self, path: pathlib.Path) -> pathlib.Path:
        if path.is_absolute() or self.wrapper is None or self.wrapper.experiment_dir is None:
            return path
        return self.wrapper.experiment_dir / path

    def _resolve_orchestrator_options(
        self,
        orchestrator_options: OrchestratorOptions | None = None,
        parallelism: int | None = None,
        tolerated_trial_failure_rate: float | None = None,
        initial_seconds_between_polls: int | None = None,
    ) -> OrchestratorOptions:
        options = orchestrator_options or self.orchestrator_options or OrchestratorOptions()
        replacements = {}
        if parallelism is not None:
            replacements["max_pending_trials"] = parallelism
        if tolerated_trial_failure_rate is not None:
            replacements["tolerated_trial_failure_rate"] = tolerated_trial_failure_rate
        if initial_seconds_between_polls is not None:
            replacements["init_seconds_between_polls"] = initial_seconds_between_polls
        return replace(options, **replacements) if replacements else options

    def run_trials(
        self,
        max_trials: int | None = None,
        parallelism: int | None = None,
        tolerated_trial_failure_rate: float | None = None,
        initial_seconds_between_polls: int | None = None,
        orchestrator_options: OrchestratorOptions | None = None,
    ) -> None:
        """Run trials using the complete BOA/Ax ``OrchestratorOptions``."""

        options = self._resolve_orchestrator_options(
            orchestrator_options=orchestrator_options,
            parallelism=parallelism,
            tolerated_trial_failure_rate=tolerated_trial_failure_rate,
            initial_seconds_between_polls=initial_seconds_between_polls,
        )
        storage_config = getattr(self, "_storage_config", None)
        orchestrator = Orchestrator(
            experiment=self._experiment,
            generation_strategy=self._generation_strategy_or_choose(),
            options=options,
            db_settings=db_settings_from_storage_config(storage_config) if storage_config is not None else None,
        )
        self._last_orchestrator = orchestrator
        if max_trials is not None:
            orchestrator.run_n_trials(max_trials=max_trials)
        else:
            orchestrator.run_all_trials()

    def save_data(self, *, metrics_to_end: bool = False, **to_csv_kwargs) -> None:
        """Save Ax Client state and BOA's optimization summary CSV."""

        self.client_filepath.parent.mkdir(parents=True, exist_ok=True)
        self.optimization_csv.parent.mkdir(parents=True, exist_ok=True)
        self.save_to_json_file(filepath=str(self.client_filepath))
        df = self.summarize()
        if metrics_to_end:
            metric_names = list(self.experiment.metrics.keys())
            metric_cols = [col for col in df.columns if col in metric_names]
            df = df[[col for col in df.columns if col not in metric_cols] + metric_cols]
        to_csv_kwargs.setdefault("na_rep", "NA")
        df.to_csv(self.optimization_csv, index=False, **to_csv_kwargs)
        logger.info(f"Saved client to `{self.client_filepath}`.")
        logger.info(f"Saved optimization summary to `{self.optimization_csv}`.")

    def report_results(self, force_refit: bool = False) -> None:
        """Save current state and log a concise optimization progress update."""

        self.save_data()
        try:
            trials = self.get_best_trials(use_model_predictions=False)
            best_trial_map = {idx: trial_dict["means"] for idx, trial_dict in trials.items()} if trials else {}
            best_trial_str = f"\nBest trial so far: {pformat(best_trial_map)}"
        except Exception as e:  # pragma: no cover
            best_trial_str = ""
            logger.exception(e)

        running_trials = [
            str(trial.index)
            for trial in self.experiment.trials.values()
            if trial.status in {TrialStatus.RUNNING, TrialStatus.STAGED}
        ]
        running_trials = running_trials[0] if len(running_trials) == 1 else running_trials
        generation_node = getattr(self.generation_strategy, "current_node_name", None)
        update = (
            f"Trials so far: {len(self.experiment.trials)}"
            f"\nCurrently running trials: {running_trials}"
            f"\nWill produce next trials from node: {generation_node}"
            f"{best_trial_str}"
        )
        logger.info(update)

    def get_best_trials(self, use_model_predictions: bool = False) -> dict[int, dict]:
        """Return BOA's compact best-trial/Pareto summary using Ax Client APIs."""

Scheduler = BOAClient