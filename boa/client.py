from __future__ import annotations

import copy
import pathlib
import time
from dataclasses import asdict, replace
from pprint import pformat
from typing import Any, Iterable, Optional

from boa.__version__ import __version__
from boa.ax_api import (
    ChoiceParameterConfig,
    Client,
    CORE_CLASS_DECODER_REGISTRY,
    CORE_CLASS_ENCODER_REGISTRY,
    CORE_DECODER_REGISTRY,
    CORE_ENCODER_REGISTRY,
    DerivedParameterConfig,
    MultiObjective,
    object_from_json,
    object_to_json,
    OptimizationConfig,
    OrchestratorOptions,
    RangeParameterConfig,
    TrialStatus,
    choose_generation_strategy_new,
    optimization_config_from_string,
)
from boa.config import BOAConfig, BOAMetric, MetricType
from boa.definitions import PathLike
from boa.logger import get_logger
from boa.metrics.metrics import get_metric_from_config
from boa.runner import WrappedJobRunner
from boa.wrappers.base_wrapper import BaseWrapper

logger = get_logger()

PARAMETER_CONFIGS = {
    "choice": ChoiceParameterConfig,
    "range": RangeParameterConfig,
    "derived": DerivedParameterConfig,
}

TERMINAL_STATUSES = {
    TrialStatus.COMPLETED,
    TrialStatus.FAILED,
    TrialStatus.ABANDONED,
    TrialStatus.EARLY_STOPPED,
}


class BOAClient(Client):
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

    @property
    def experiment(self):
        return self._experiment

    @property
    def runner(self):
        return self.experiment.runner

    @property
    def generation_strategy(self):
        return self._generation_strategy_or_choose()

    @property
    def adapter(self):
        return self.generation_strategy.adapter

    @property
    def model(self):
        return self.adapter

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

    def run_n_trials(self, max_trials: int, **kwargs) -> None:
        self.run_trials(max_trials=max_trials, **kwargs)

    def run_trials(
        self,
        max_trials: int | None = None,
        parallelism: int | None = None,
        tolerated_trial_failure_rate: float | None = None,
        initial_seconds_between_polls: int | None = None,
        orchestrator_options: OrchestratorOptions | None = None,
    ) -> None:
        options = self._resolve_orchestrator_options(
            orchestrator_options=orchestrator_options,
            parallelism=parallelism,
            tolerated_trial_failure_rate=tolerated_trial_failure_rate,
            initial_seconds_between_polls=initial_seconds_between_polls,
        )
        total_trials = max_trials if max_trials is not None else options.total_trials
        if total_trials is None:
            raise ValueError("`max_trials` or `orchestrator.total_trials` must be set to run BOA trials.")

        completed = 0
        failed = 0
        while completed + failed < total_trials:
            remaining = total_trials - completed - failed
            batch_size = min(remaining, options.max_pending_trials or remaining)
            next_trials = self.get_next_trials(max_trials=batch_size)
            if not next_trials:
                break
            trials = [self.experiment.trials[index] for index in next_trials]
            self.runner.run_multiple(trials)
            statuses = self._wait_for_trials(trials=trials, options=options)
            for trial_index, status in statuses.items():
                if status == TrialStatus.COMPLETED:
                    self._complete_with_metric_data(trial_index=trial_index)
                    completed += 1
                else:
                    self._save_or_update_trial_in_db_if_possible(
                        experiment=self.experiment,
                        trial=self.experiment.trials[trial_index],
                    )
                    failed += 1
            self.report_results()

    def _wait_for_trials(self, trials, options: OrchestratorOptions) -> dict[int, TrialStatus]:
        pending = {trial.index: trial for trial in trials}
        statuses = {}
        sleep_for = options.init_seconds_between_polls or 1
        start = time.time()
        while pending:
            polled = self.runner.poll_trial_status(pending.values())
            for status, trial_indices in polled.items():
                for trial_index in trial_indices:
                    if status in TERMINAL_STATUSES:
                        statuses[trial_index] = status
                        pending.pop(trial_index, None)
            if pending:
                if options.ttl_seconds_for_trials is not None and time.time() - start > options.ttl_seconds_for_trials:
                    for trial in pending.values():
                        trial.mark_failed(unsafe=True)
                        statuses[trial.index] = TrialStatus.FAILED
                    break
                time.sleep(sleep_for)
                sleep_for = max(
                    options.min_seconds_before_poll,
                    sleep_for * options.seconds_between_polls_backoff_factor,
                )
        return statuses

    def _complete_with_metric_data(self, trial_index: int) -> None:
        raw_data, progression = self._fetch_trial_raw_data(trial_index=trial_index)
        if raw_data:
            self.attach_data(trial_index=trial_index, raw_data=raw_data, progression=progression)
        trial = self.experiment.trials[trial_index]
        if trial.status != TrialStatus.COMPLETED:
            trial.mark_completed(unsafe=True)
        self._save_or_update_trial_in_db_if_possible(experiment=self.experiment, trial=trial)

    def _fetch_trial_raw_data(self, trial_index: int) -> tuple[dict[str, float | tuple[float, float]], int | None]:
        trial = self.experiment.trials[trial_index]
        parameters = dict(trial.arm.parameters)
        trial_metadata = {
            "parameterization": parameters,
            "run_metadata": trial.run_metadata,
            "trial_index": trial_index,
        }
        raw_data = {}
        progression = None
        for metric_name, metric in self.experiment.metrics.items():
            if not hasattr(metric, "fetch"):
                continue
            metric_progression, value = metric.fetch(trial_index=trial_index, trial_metadata=trial_metadata)
            if progression is None:
                progression = metric_progression
            raw_data[metric_name] = value
        return raw_data, progression

    def save_data(self, *, metrics_to_end: bool = False, **to_csv_kwargs) -> None:
        self.client_filepath.parent.mkdir(parents=True, exist_ok=True)
        self.optimization_csv.parent.mkdir(parents=True, exist_ok=True)
        self.save_to_json_file(filepath=str(self.client_filepath))
        df = self.summarize()
        if metrics_to_end:
            metric_names = list(self.experiment.metrics.keys())
            metric_cols = [col for col in df.columns if col in metric_names]
            df = df[[col for col in df.columns if col not in metric_cols] + metric_cols]
        for metric_name in self.experiment.metrics:
            if metric_name not in df.columns:
                df[metric_name] = None
        to_csv_kwargs.setdefault("na_rep", "NA")
        df.to_csv(self.optimization_csv, index=False, **to_csv_kwargs)
        logger.info(f"Saved client to `{self.client_filepath}`.")
        logger.info(f"Saved optimization summary to `{self.optimization_csv}`.")

    def report_results(self, force_refit: bool = False) -> None:
        self.save_data()
        try:
            trials = self.get_best_trials(use_model_predictions=False)
            best_trial_map = {idx: trial_dict["means"] for idx, trial_dict in trials.items()} if trials else {}
            best_trial_str = f"\nBest trial so far: {pformat(best_trial_map)}"
        except Exception as e:
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
        if self.experiment.optimization_config.is_moo_problem:
            try:
                return {
                    int(trial_index): dict(params=params, means=means, cov_matrix=None)
                    for params, means, trial_index, _ in self.get_pareto_frontier(
                        use_model_predictions=use_model_predictions
                    )
                }
            except Exception as e:
                logger.warning(f"Problem generating Pareto frontier summary. Exception: {e!r}")
                return {}
        try:
            params, means, trial_index, _ = self.get_best_parameterization(use_model_predictions=use_model_predictions)
        except Exception as e:
            logger.warning(f"Problem generating best trial summary. Exception: {e!r}")
            return {}
        return {int(trial_index): dict(params=params, means=means, cov_matrix=None)}

    def best_raw_trials(
        self,
        optimization_config: Optional[OptimizationConfig] = None,
        trial_indices: Optional[Iterable[int]] = None,
        use_model_predictions: bool = False,
        *args,
        **kwargs,
    ) -> dict:
        return self.get_best_trials(use_model_predictions=False)

    def best_fitted_trials(
        self,
        optimization_config: Optional[OptimizationConfig] = None,
        trial_indices: Optional[Iterable[int]] = None,
        use_model_predictions: bool = True,
        *args,
        **kwargs,
    ) -> dict:
        return self.get_best_trials(use_model_predictions=use_model_predictions)

    def _to_json_snapshot(self) -> dict[str, Any]:
        snapshot = super()._to_json_snapshot()
        snapshot["boa_version"] = __version__
        snapshot["wrapper"] = (
            object_to_json(
                self.wrapper,
                encoder_registry=CORE_ENCODER_REGISTRY,
                class_encoder_registry=CORE_CLASS_ENCODER_REGISTRY,
            )
            if self.wrapper is not None
            else None
        )
        snapshot["orchestrator_options"] = (
            object_to_json(
                self.orchestrator_options,
                encoder_registry=CORE_ENCODER_REGISTRY,
                class_encoder_registry=CORE_CLASS_ENCODER_REGISTRY,
            )
            if self.orchestrator_options is not None
            else None
        )
        snapshot["client_filepath"] = str(self._client_filepath)
        snapshot["optimization_csv"] = str(self._optimization_csv)
        return snapshot

    @classmethod
    def _from_json_snapshot(
        cls,
        snapshot: dict[str, Any],
        storage_config=None,
    ):
        client = super()._from_json_snapshot(snapshot=snapshot, storage_config=storage_config)
        wrapper = (
            object_from_json(
                snapshot["wrapper"],
                decoder_registry=CORE_DECODER_REGISTRY,
                class_decoder_registry=CORE_CLASS_DECODER_REGISTRY,
            )
            if snapshot.get("wrapper") is not None
            else None
        )
        client.wrapper = wrapper
        client.orchestrator_options = (
            object_from_json(
                snapshot["orchestrator_options"],
                decoder_registry=CORE_DECODER_REGISTRY,
                class_decoder_registry=CORE_CLASS_DECODER_REGISTRY,
            )
            if snapshot.get("orchestrator_options") is not None
            else None
        )
        client._client_filepath = pathlib.Path(snapshot.get("client_filepath", "client.json"))
        client._optimization_csv = pathlib.Path(snapshot.get("optimization_csv", "optimization.csv"))
        client.attach_wrapper(wrapper)
        return client

    def attach_wrapper(self, wrapper: BaseWrapper | None):
        if wrapper is None:
            return self
        self.wrapper = wrapper
        runner = getattr(self.experiment, "runner", None)
        if runner is not None and hasattr(runner, "wrapper"):
            runner.wrapper = wrapper
        for metric in self.experiment.metrics.values():
            if hasattr(metric, "wrapper"):
                metric.wrapper = wrapper
        return self


def _parameter_config_from_dict(parameter: dict[str, Any]):
    parameter = copy.deepcopy(parameter)
    parameter_type = parameter.pop("type")
    if parameter_type == "fixed":
        parameter["values"] = [parameter.pop("value")]
        parameter.setdefault("is_ordered", False)
        return ChoiceParameterConfig(**parameter)
    if parameter_type == "range" and isinstance(parameter.get("bounds"), list):
        parameter["bounds"] = tuple(parameter["bounds"])
    return PARAMETER_CONFIGS[parameter_type](**parameter)


def _metric_names_from_optimization(config: BOAConfig) -> list[str]:
    opt_config = optimization_config_from_string(
        objective_str=config.optimization.objective,
        outcome_constraint_strs=config.optimization.outcome_constraints,
    )
    metric_names = []
    if isinstance(opt_config.objective, MultiObjective):
        for objective in opt_config.objective.objectives:
            metric_names.extend(objective.metric_names)
    else:
        metric_names.extend(opt_config.objective.metric_names)
    metric_names.extend(config.optimization.tracking_metrics)
    for constraint in opt_config.outcome_constraints:
        metric_names.extend(constraint.metric_names)
    return list(dict.fromkeys(metric_names))


def _configure_generation_strategy(client: BOAClient, config: BOAConfig) -> None:
    if config.generation_strategy is None:
        return
    generation_strategy = config.generation_strategy
    if generation_strategy.struct.method == "custom":
        client.set_generation_strategy(
            generation_strategy=choose_generation_strategy_new(
                struct=generation_strategy.struct,
                model_config=generation_strategy.model_config,
                botorch_acqf_class=generation_strategy.botorch_acqf_class,
            )
        )
        return
    client.configure_generation_strategy(**asdict(generation_strategy.struct))


def get_client(config: BOAConfig, wrapper: BaseWrapper | None = None, runner=None, **kwargs) -> BOAClient:
    client = BOAClient(wrapper=wrapper, orchestrator_options=config.orchestrator, **kwargs)
    parameters = [_parameter_config_from_dict(parameter) for parameter in config.parameters]
    client.configure_experiment(
        parameters=parameters,
        parameter_constraints=config.parameter_constraints,
        name=config.script_options.exp_name,
    )
    client.configure_optimization(
        objective=config.optimization.objective,
        outcome_constraints=config.optimization.outcome_constraints,
        pruning_target_parameterization=config.optimization.pruning_target_parameterization,
    )
    _configure_generation_strategy(client=client, config=config)

    if runner is None:
        runner = WrappedJobRunner(wrapper=wrapper)
    client.configure_runner(runner=runner)

    if config.optimization.tracking_metrics:
        client.configure_tracking_metrics(metric_names=config.optimization.tracking_metrics)

    metrics = []
    for name in _metric_names_from_optimization(config):
        metric_conf = config.optimization.metrics.get(name)
        if metric_conf is None:
            metric_conf = BOAMetric(metric=name, metric_type=MetricType.PASSTHROUGH)
        metrics.append(get_metric_from_config(config=metric_conf, wrapper=wrapper))
    if metrics:
        client.configure_metrics(metrics=metrics)
    if wrapper is not None and not getattr(wrapper, "metric_names", None):
        wrapper.metric_names = list(client.experiment.metrics.keys())
    return client


Scheduler = BOAClient
