from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Optional

import ax.early_stopping.strategies as early_stopping_strats
import ax.global_stopping.strategies as global_stopping_strats
from ax.modelbridge.generation_node import GenerationStep
from ax.modelbridge.registry import Models
from ax.service.utils.instantiation import TParameterRepresentation
from ax.service.utils.scheduler_options import SchedulerOptions

if TYPE_CHECKING:
    from .config import BOAMetric


def _convert_noton_type(converter, type_, default_if_none=None) -> Any:
    def type_converter(val):
        if default_if_none is not None and val is None:
            if isinstance(default_if_none, Callable):
                return default_if_none()
            return default_if_none
        if not isinstance(val, type_):
            return converter(val)
        return val

    return type_converter


def _metric_converter(ls: list[BOAMetric | dict]) -> list[BOAMetric]:
    from .config import BOAMetric

    for i, metric in enumerate(ls):
        if isinstance(metric, dict):
            ls[i] = BOAMetric(**metric)
    return ls


def _gen_strat_converter(gs: Optional[dict] = None) -> dict:
    if len(gs) > 1 and "steps" in gs:
        raise ValueError("Cannot specify both `steps` and options for automatic generation strategy.")
    if gs.get("steps"):
        steps = []
        for i, step in enumerate(gs["steps"]):
            if isinstance(step, GenerationStep):
                gs["steps"][i] = step
                steps.append(step)
                continue
            try:
                step["model"] = Models[step["model"]]
            except KeyError:
                step["model"] = Models(step["model"])
            gs["steps"][i] = GenerationStep(**step)
    return gs


def _load_stopping_strategy(d: Optional[dict], module: ModuleType):

    if (
        isinstance(
            d, (early_stopping_strats.BaseEarlyStoppingStrategy, global_stopping_strats.BaseGlobalStoppingStrategy)
        )  # loading from reserializilization and work already done
        or not d
    ):  # option set to None or False truth value
        return d
    if "type" not in d:
        raise ValueError("Type missing from stopping strategy key")  # can't work with it if type not set
    type_ = d.pop("type")
    for key, value in d.items():
        if isinstance(value, dict):
            d[key] = _load_stopping_strategy(d=value, module=module)
    cls: type = getattr(module, type_)
    instance = cls(**d)
    return instance


def _scheduler_converter(scheduler_options: dict) -> SchedulerOptions:
    if "early_stopping_strategy" in scheduler_options:
        scheduler_options["early_stopping_strategy"] = _load_stopping_strategy(
            d=scheduler_options["early_stopping_strategy"], module=early_stopping_strats
        )

    if "global_stopping_strategy" in scheduler_options:
        scheduler_options["global_stopping_strategy"] = _load_stopping_strategy(
            d=scheduler_options["global_stopping_strategy"], module=global_stopping_strats
        )

    return SchedulerOptions(**scheduler_options)


def _parameter_normalization(
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
