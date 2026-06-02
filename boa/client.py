from __future__ import annotations

import copy
import pathlib
import time
from dataclasses import asdict, replace
from pprint import pformat
from typing import Any, Iterable, Optional
import multiprocessing

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
    db_settings_from_storage_config,
    Orchestrator,
    RangeParameterConfig,
    TrialStatus,
    choose_generation_strategy_new,
    optimization_config_from_string,
    IRunner,
    Runner,
    Trial,
)
from boa.config import BOAConfig, BOAMetric, MetricType
from boa.definitions import PathLike
from boa.logger import get_logger
from boa.metrics.metrics import get_metric_from_config
from boa.runner import WrappedJobRunner
from boa.wrappers.base_wrapper import BaseWrapper
from boa.metrics.synthetic_funcs import get_synth_func
from boa.metaclasses import RunnerRegister
import logging
import concurrent.futures
from typing import Any, Dict, Iterable, Set
from collections import defaultdict
from boa.utils import serialize_init_args
from boa.metrics.metrics import PassThrough


import os
import time
from typing import Any, Mapping

import numpy as np
from ax.api.client import Client
from ax.api.configs import RangeParameterConfig
from ax.api.protocols.metric import IMetric
from ax.api.protocols.runner import IRunner, TrialStatus
from ax.api.types import TParameterization

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
        total_trials: int | None = None 
    ) -> OrchestratorOptions:
        options = orchestrator_options or self.orchestrator_options or OrchestratorOptions()
        replacements = {}
        if parallelism is not None:
            replacements["max_pending_trials"] = parallelism
        if tolerated_trial_failure_rate is not None:
            replacements["tolerated_trial_failure_rate"] = tolerated_trial_failure_rate
        if initial_seconds_between_polls is not None:
            replacements["init_seconds_between_polls"] = initial_seconds_between_polls
        if total_trials is not None:
            replacements["total_trials"] = total_trials
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
        ignore_global_stopping_strategy: bool = False
    ) -> None:
        kw = {}
        if len(self.experiment.trials):
            total_trials = len(self.experiment.trials)
            if isinstance(orchestrator_options, OrchestratorOptions):
                total_trials = max(orchestrator_options.total_trials, total_trials)
            kw["total_trials"] = total_trials + max_trials
        options = self._resolve_orchestrator_options(
            orchestrator_options=orchestrator_options,
            parallelism=parallelism,
            tolerated_trial_failure_rate=tolerated_trial_failure_rate,
            initial_seconds_between_polls=initial_seconds_between_polls,
            **kw
        )
        orchestrator = Orchestrator(
            experiment=self._experiment,
            generation_strategy=self._generation_strategy_or_choose(),
            options=options,
            db_settings=db_settings_from_storage_config(self._storage_config)
            if self._storage_config is not None
            else None,
        )
        max_trials = max_trials or orchestrator.options.total_trials
        # Note: This Orchestrator call will handle storage internally
        orchestrator.run_n_trials(max_trials=max_trials, ignore_global_stopping_strategy=ignore_global_stopping_strategy, idle_callback=self.report_results)
        # orchestrator.run_n_trials(max_trials=max_trials)

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

    def report_results(self, *args, force_refit: bool = False) -> None:
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
        parameter.setdefault("parameter_type", type(parameter["value"]).__name__) 
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
    # client = Client(**kwargs)
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
        # runner = WrappedJobRunner2(wrapper=wrapper)
        # runner = WrappedJobRunner3(wrapper=wrapper)
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







    # client = Client()
    # # Define six float parameters for the Hartmann6 function
    # parameters = [
    #     RangeParameterConfig(
    #         name="x1", parameter_type="float", bounds=(-5, 10)
    #     ),
    #     RangeParameterConfig(
    #         name="x2", parameter_type="float", bounds=(0, 15)
    #     ),
    # ]

    # client.configure_experiment(
    #     parameters=parameters,
    #     # The following arguments are only necessary when saving to the DB
    #     name="branin_experiment",
    #     description="Optimization of the branin function",
    #     owner="developer",
    # )
    # client.configure_optimization(objective="-branin")
    # runner = MockRunner()
    # client.configure_runner(runner=runner)
    # hartmann6_metric = MockMetric(name="branin")
    # client.configure_metrics(metrics=[hartmann6_metric])

    # branin_pt = PassThrough(name="branin", wrapper=wrapper)
    # client.configure_metrics(metrics=[branin_pt])

    return client


Scheduler = BOAClient


branin = get_synth_func("branin")

# Hartmann6 function
def hartmann6(x1, x2, x3, x4, x5, x6):
    alpha = np.array([1.0, 1.2, 3.0, 3.2])
    A = np.array([
        [10, 3, 17, 3.5, 1.7, 8],
        [0.05, 10, 17, 0.1, 8, 14],
        [3, 3.5, 1.7, 10, 17, 8],
        [17, 8, 0.05, 10, 0.1, 14]
    ])
    P = 10**-4 * np.array([
        [1312, 1696, 5569, 124, 8283, 5886],
        [2329, 4135, 8307, 3736, 1004, 9991],
        [2348, 1451, 3522, 2883, 3047, 6650],
        [4047, 8828, 8732, 5743, 1091, 381]
    ])

    outer = 0.0
    for i in range(4):
        inner = 0.0
        for j, x in enumerate([x1, x2, x3, x4, x5, x6]):
            inner += A[i, j] * (x - P[i, j])**2
        outer += alpha[i] * np.exp(-inner)
    return -outer

class MockRunner(IRunner):
    def run_trial(
        self, trial_index: int, parameterization: TParameterization
    ) -> dict[str, Any]:
        file_name = f"{int(time.time())}.txt"

        x1 = parameterization["x1"]
        x2 = parameterization["x2"]


        result = branin(x1, x2)

        with open(file_name, "w") as f:
            f.write(f"{result}")

        return {"file_name": file_name}

    def poll_trial(
        self, trial_index: int, trial_metadata: Mapping[str, Any]
    ) -> TrialStatus:
        file_name = trial_metadata["file_name"]
        time_elapsed = time.time() - int(file_name[:4])

        if time_elapsed < 5:
            return TrialStatus.RUNNING

        return TrialStatus.COMPLETED
    

class MockMetric(IMetric):
    def fetch(
        self,
        trial_index: int,
        trial_metadata: Mapping[str, Any],
    ) -> tuple[int, float | tuple[float, float]]:
        file_name = trial_metadata["file_name"]

        with open(file_name, 'r') as file:
            value = float(file.readline())
            return (0, value)


class WrappedJobRunner2(Runner, metaclass=RunnerRegister):
    def __init__(self, wrapper: BaseWrapper = None, *args, **kwargs):

        self.wrapper = wrapper or BaseWrapper()
        self.queue = multiprocessing.Manager().Queue()
        super().__init__(*args, **kwargs)

    def run(self, trial: Trial) -> Dict[str, Any]:
        """Deploys a trial based on custom runner subclass implementation.

        Add a logging queue handler to the boa and ax root loggers to capture logs from the
        wrapper.

        Args:
            trial: The trial to deploy.

        Returns:
            Dict of run metadata from the deployment process.
        """
        parameterization = trial.arm.parameters
        file_name = f"{int(time.time())}.txt"

        x1 = parameterization["x1"]
        x2 = parameterization["x2"]


        result = branin(x1, x2)

        with open(file_name, "w") as f:
            f.write(f"{result}")

        return {"file_name": file_name}

    def run_multiple(self, trials) -> dict[int, dict[str, Any]]:
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
            status_dict[TrialStatus.COMPLETED].add(trial.index)

        return status_dict

    def to_dict(self) -> dict:
        """Convert runner to a dictionary."""

        parents = self.__class__.mro()[1:]  # index 0 is the class itself

        properties = serialize_init_args(self, parents=parents, match_private=True, exclude_fields=["wrapper", "queue"])

        properties["__type"] = self.__class__.__name__
        return properties


class WrappedJobRunner3(Runner, metaclass=RunnerRegister):
    def __init__(self, wrapper: BaseWrapper = None, *args, **kwargs):

        self.wrapper = wrapper or BaseWrapper()
        self.queue = multiprocessing.Manager().Queue()
        super().__init__(*args, **kwargs)

    def run(self, trial: Trial) -> Dict[str, Any]:
        """Deploys a trial based on custom runner subclass implementation.

        Add a logging queue handler to the boa and ax root loggers to capture logs from the
        wrapper.

        Args:
            trial: The trial to deploy.

        Returns:
            Dict of run metadata from the deployment process.
        """
        metadata = self.wrapper.run_model(trial)
        if metadata is None:
            metadata = {}
        metadata["parameterization"] = trial.arm.parameters
        return metadata

    # def run_multiple(self, trials) -> dict[int, dict[str, Any]]:
    #     """Runs a single evaluation for each of the given trials. Useful when deploying
    #     multiple trials at once is more efficient than deploying them one-by-one.
    #     Used in Ax ``Scheduler``.

    #     NOTE: By default simply loops over `run_trial`. Should be overwritten
    #     if deploying multiple trials in batch is preferable.

    #     Args:
    #         trials: Iterable of trials to be deployed, each containing arms with
    #             parameterizations to be evaluated. Can be a `Trial`
    #             if contains only one arm or a `BatchTrial` if contains
    #             multiple arms.

    #     Returns:
    #         Dict of trial index to the run metadata of that trial from the deployment
    #         process.
    #     """
    #     results = {}
    #     with concurrent.futures.ThreadPoolExecutor() as executor:
    #         trial_runs = {executor.submit(self.run, trial=trial): trial.index for trial in trials}
    #         for future in concurrent.futures.as_completed(trial_runs):
    #             trial_index = trial_runs[future]
    #             try:
    #                 results[trial_index] = future.result()
    #             except Exception as e:
    #                 logger.exception(f"Error completing run because of {e}!")
    #                 raise
    #         concurrent.futures.wait(trial_runs)

    #     return results

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
            status_dict[TrialStatus.COMPLETED].add(trial.index)

        return status_dict

    def to_dict(self) -> dict:
        """Convert runner to a dictionary."""

        parents = self.__class__.mro()[1:]  # index 0 is the class itself

        properties = serialize_init_args(self, parents=parents, match_private=True, exclude_fields=["wrapper", "queue"])

        properties["__type"] = self.__class__.__name__
        return properties