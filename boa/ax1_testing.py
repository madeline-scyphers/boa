from typing import Any, Mapping
import time
import numpy as np

from boa.runner import WrappedJobRunner
from boa.wrappers.script_wrapper import ScriptWrapper
from boa.wrappers.base_wrapper import BaseWrapper
from boa.ax_api import (
    RangeParameterConfig, 
    ChoiceParameterConfig, 
    DerivedParameterConfig,
    CLASS_TO_REVERSE_REGISTRY,
    TParameterRepresentation,
    Client,
    choose_generation_strategy_new,
    ModelConfig,
    GenerationStrategyDispatchStruct,
    IRunner,
    IMetric,
    TrialStatus,
    TParameterization,
    optimization_config_from_string,
    MultiObjective,
    ScalarizedObjective
)
from boa.metrics.metrics import get_metric_from_config
from boa.scripts.script_wrappers import BraninWrapper
from boa.config.config import MetricType, BOAMetric
from attrs import define
from enum import StrEnum


param_mapping = {
    "choice": ChoiceParameterConfig,
    "range": RangeParameterConfig,
    "derived": DerivedParameterConfig
}

def parameter_normalization(
    parameters: list[TParameterRepresentation] | dict[str, dict]
) -> list[TParameterRepresentation]:
    if isinstance(parameters, list):
        return parameters
    new_parameters = []
    for param, d in parameters.items():
        if not isinstance(d, dict):
            d = {"value": d, "type": "fixed"}
        d["name"] = param  # Add "name" attribute for each parameter
        # remove bounds on fixed params
        if d.get("type", "") == "fixed" and "bounds" in d:
            del d["bounds"]
        # Remove value on range params
        if d.get("type", "") == "range" and "value" in d:
            del d["value"]

        new_parameters.append(d)
    return new_parameters


def get_model_from_reverse_registry(model_name: str) -> type[Any]:
    for cls, reverse_registry in CLASS_TO_REVERSE_REGISTRY.items():
        if model_name in reverse_registry:
            return reverse_registry[model_name]


def recurse_model_config(obj: dict | list):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                obj[k] = recurse_model_config(v)
                continue
            if (model := get_model_from_reverse_registry(v)) is not None:
                obj[k] = model
    if isinstance(obj, list):
        for i, v in enumerate(obj):
            if isinstance(v, (dict, list)):
                obj[i] = recurse_model_config(v)
                continue
            if (model := get_model_from_reverse_registry(v)) is not None:
                obj[i] = model
    return obj

  
def get_client(config: dict, runner=None):
    client = Client()
    parameters = [param_mapping[param.pop("type")](**param) for param in parameter_normalization(config["parameters"])]
    del config["parameters"]
    client.configure_experiment(
        parameters=parameters,
        parameter_constraints=config.pop("parameter_constraints", None)
    )
    client.configure_optimization(
        objective=config["optimization"]["objective"],
        outcome_constraints=config["optimization"].get("outcome_constraints", None)
    )
    opt_config = optimization_config_from_string(
        objective_str=config["optimization"]["objective"],
        outcome_constraint_strs=config["optimization"].get("outcome_constraints", None)
    )

    if config.get("generation_strategy", {}).get("method", "") == "custom":
        kw = {}
        if (model_config := config["generation_strategy"].get("model_config", None)) is not None:
            kw["model_config"] = ModelConfig(
                **recurse_model_config(model_config)
            )
        if (botorch_acqf_class := config["generation_strategy"].get("botorch_acqf_class", None)) is not None:
            kw["botorch_acqf_class"] = get_model_from_reverse_registry(botorch_acqf_class)
        kw["struct"] = GenerationStrategyDispatchStruct(**config["generation_strategy"])
        gs = choose_generation_strategy_new(**kw)
        client.set_generation_strategy(generation_strategy=gs)
    else:
        client.configure_generation_strategy(
            **config.get("generation_strategy", {})
        )
    if runner is None:
        runner = MockRunner()
        wrapper = None
    else:
        wrapper = runner.wrapper
    client.configure_runner(runner=runner)
    if (tracking_metrics := config["optimization"].pop("tracking_metrics", [])):
        client.configure_tracking_metrics(metric_names=tracking_metrics)
    
    metric_names = []
    if isinstance(opt_config.objective, MultiObjective):
        for obj in opt_config.objective.objectives:
            for name in obj.metric_names:
                metric_names.append(name)
    else:
        for name in opt_config.objective.metric_names:
            metric_names.append(name)
    metric_names.extend(tracking_metrics)
    metric_dicts = config["optimization"].get("metrics", {})
    metrics = []
    for name in metric_names:
        metric_type = MetricType.PASSTHROUGH
        if name in metric_dicts:
            metric_type=MetricType.from_str_or_enum(metric_dicts[name].get("metric_type", MetricType.PASSTHROUGH))
        metric_conf = BOAMetric(
            metric=name,
            metric_type=metric_type
        )
        metrics.append(get_metric_from_config(config=metric_conf))
    client.configure_metrics(metrics=metrics)
    return client


@define
class MetricTest:
    metric: str
    wrapper: BaseWrapper = None
    metric_type: MetricType = MetricType.PASSTHROUGH


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

hartmann6(0.1, 0.45, 0.8, 0.25, 0.552, 1.0)

class MockRunner(IRunner):
    def run_trial(
        self, trial_index: int, parameterization: TParameterization
    ) -> dict[str, Any]:
        file_name = f"{int(time.time())}.txt"

        x1 = parameterization["x1"]
        x2 = parameterization["x2"]
        x3 = parameterization["x3"]
        x4 = parameterization["x4"]
        x5 = parameterization["x5"]
        x6 = parameterization["x6"]

        result = hartmann6(x1, x2, x3, x4, x5, x6)

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