from __future__ import annotations

import pathlib
from dataclasses import asdict as dc_asdict
from dataclasses import is_dataclass
from enum import Enum
from types import ModuleType
from typing import Any, Optional, Union

import ax.early_stopping.strategies as early_stopping_strats
import ax.global_stopping.strategies as global_stopping_strats
from attr import asdict
from attrs import Factory, converters, define, field, fields_dict
from ax.modelbridge.generation_node import GenerationStep
from ax.modelbridge.registry import Models
from ax.service.scheduler import SchedulerOptions
from ax.service.utils.instantiation import TParameterRepresentation

from boa.definitions import PathLike
from boa.utils import deprecation
from boa.wrappers.wrapper_utils import load_jsonlike

__all__ = ["Objective", "Metric", "MetricType", "ScriptOptions", "Config"]


@define
class ToDict:
    def to_dict(self):
        def vs(inst, attrib, val):
            if is_dataclass(val):
                return dc_asdict(val)
            return val

        return asdict(self, value_serializer=vs)


def _convert_on_type(converter, type_, default_if_none=None) -> Any:
    def type_converter(val):
        if default_if_none is not None and val is None:
            return default_if_none
        if isinstance(val, type_):
            return converter(val)
        return val

    return type_converter


def _convert_on_dict(converter):
    return _convert_on_type(converter=converter, type_=dict)


class MetricType(Enum):
    METRIC = "metric"
    BOA_METRIC = "boa_metric"
    SKLEARN_METRIC = "sklearn_metric"
    SYNTHETIC_METRIC = "synthetic_metric"
    PASSTHROUGH = "PassThrough"


def _metric_type_converter(type_: MetricType | str) -> MetricType:
    if isinstance(type_, MetricType):
        return type_
    try:
        return MetricType[type_]
    except KeyError:
        return MetricType(type_)


@define
class Metric(ToDict):
    metric: Optional[str] = None
    name: Optional[str] = field(default=None, converter=converters.optional(str))
    type_: Optional[MetricType | str] = field(
        default=MetricType.METRIC, converter=converters.optional(_metric_type_converter)
    )
    noise_sd: Optional[float] = 0
    minimize: Optional[bool] = field(default=True, kw_only=True)
    info_only: bool = False
    weight: Optional[float] = None
    properties: Optional[dict] = None

    def __init__(self, *args, lower_is_better: Optional[bool] = None, **kwargs):
        if lower_is_better is not None:
            if "minimize" in kwargs:
                raise TypeError("Specify either `lower_is_better` or `minimize` but not both")
            kwargs["minimize"] = lower_is_better
        self.__attrs_init__(*args, **kwargs)

    def __attrs_post_init__(self):
        if not self.metric and not self.name:
            raise TypeError("Must specify at least metric name or metric")
        if self.name is None:
            self.name = self.metric
        elif self.metric is None:
            self.type_ = MetricType.PASSTHROUGH


def _metric_converter(ls: list[Metric | dict]) -> list[Metric]:
    for i, metric in enumerate(ls):
        if isinstance(metric, dict):
            ls[i] = Metric(**metric)
    return ls


@define
class Objective(ToDict):
    metrics: list[Metric] = field(converter=_metric_converter)
    outcome_constraints: Optional[list[str]] = Factory(list)
    objective_thresholds: Optional[list[str]] = Factory(list)
    minimize: Optional[bool] = None


@define
class ScriptOptions(ToDict):
    rel_to_config: Optional[bool] = None
    rel_to_launch: Optional[bool] = True
    base_path: Optional[PathLike] = None
    wrapper_name: str = "Wrapper"
    append_timestamp: bool = True
    wrapper_path: str = "wrapper.py"
    working_dir: str = "."
    experiment_dir: Optional[PathLike] = None
    output_dir: Optional[PathLike] = None
    write_configs: Optional[str] = None
    run_model: Optional[str] = None
    set_trial_status: Optional[str] = None
    fetch_trial_data: Optional[str] = None

    def __attrs_post_init__(self):
        if (self.rel_to_config and self.rel_to_launch) or (not self.rel_to_config and not self.rel_to_launch):
            raise TypeError("Must specify exactly one of rel_to_here or rel_to_config")

        if not self.base_path:
            if self.rel_to_config:
                raise TypeError(
                    "Must specify path to config directory in `ScriptOptions` dataclass when using rel-to-config"
                    "as the `base_path` argument."
                    "If you are an external user, the easiest way to ensure this, is to use the Config.from_jsonlike"
                    "class constructor, with either `rel_to_config` set to true in the config file or rel_to_config"
                    "set to true as an argument (to override what is in the config). This will automatically set "
                    "the `base_path` argument for `ScriptOptions`."
                )
            self.base_path = pathlib.Path.cwd()

        self.wrapper_path = self._make_path_absolute(self.base_path, self.wrapper_path)
        self.working_dir = self._make_path_absolute(self.base_path, self.working_dir)
        self.experiment_dir = self._make_path_absolute(self.base_path, self.experiment_dir)

    @staticmethod
    def _make_path_absolute(base_path, path):
        if not path:
            return path
        path = pathlib.Path(path)
        if not path.is_absolute():
            path = base_path / path
        return path.resolve()


def _gen_step_converter(steps: Optional[list[dict | GenerationStep]]) -> list[GenerationStep]:
    gs = []
    for i, step in enumerate(steps):
        if isinstance(step, GenerationStep):
            gs.append(step)
            continue
        try:
            step["model"] = Models[step["model"]]
        except KeyError:
            step["model"] = Models(step["model"])
        gs.append(GenerationStep(**step))
    return gs


def _load_stopping_strategy(d: dict, module: ModuleType):
    if "type" not in d:
        return d
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
        d["name"] = param  # Add "name" attribute for each parameter
        # remove bounds on fixed params
        if d.get("type", "") == "fixed" and "bounds" in d:
            del d["bounds"]
        # Remove value on range params
        if d.get("type", "") == "range" and "value" in d:
            del d["value"]

        new_parameters.append(d)
    return new_parameters


@define
class Config(ToDict):
    objective: Objective = field(converter=_convert_on_dict(lambda d: Objective(**d)))  #
    parameters: list[TParameterRepresentation] = field(converter=_parameter_normalization)  #
    generation_steps: Optional[list[GenerationStep]] = field(
        default=None, converter=converters.optional(_gen_step_converter)
    )  #
    scheduler: Optional[SchedulerOptions] = field(
        factory=SchedulerOptions, converter=_convert_on_dict(_scheduler_converter)
    )
    name: str = "boa_runs"
    parameter_constraints: list[str] = Factory(list)  #
    model_options: Optional[dict | list] = None  #
    script_options: Optional[ScriptOptions | dict] = field(
        factory=ScriptOptions, converter=_convert_on_dict(lambda d: ScriptOptions(**d))
    )  #
    parameter_keys: str | list[Union[str, list[str], list[Union[str, int]]]] = None

    _config_path: Optional[PathLike] = None

    @classmethod
    def from_jsonlike(cls, file, rel_to_config: Optional[bool] = None):
        config_path = pathlib.Path(file).resolve()
        config = load_jsonlike(config_path, normalize=False)

        config = cls.convert_deprecated(configd=config)

        script_options = config.get("script_options", {})
        rel_to_config = rel_to_config or script_options.get(
            "rel_to_config", fields_dict(ScriptOptions)["rel_to_config"].default
        )
        if rel_to_config:
            if "script_options" not in config:
                config["script_options"] = {}
            # we set rel_to_config to True in case it was passed in to override config
            config["script_options"]["rel_to_config"] = True
            config["script_options"]["rel_to_launch"] = False
            config["script_options"]["base_path"] = config_path.parent

        return cls(**config, config_path=file)

    # @classmethod
    # def generate_default_config(cls):
    #     ...

    @classmethod
    def convert_deprecated(cls, configd: dict) -> dict:
        if "optimization_options" not in configd:
            return configd
        deprecation(
            "Config format is deprecated, consult documentation for current format to write your configuration file.",
            "1.0",
        )
        config = {}
        opt_ops = configd["optimization_options"]

        #####################################################
        # copy over config things that didn't change
        for key in ["parameters", "parameter_constraints", "model_options", "script_options", "parameter_keys"]:
            if key in configd:
                config[key] = configd[key]

        #####################################################
        # copy objective over and then process slight changes
        config["objective"] = opt_ops["objective_options"]

        # rename old objectives key to metrics key
        config["objective"]["metrics"] = config["objective"].pop("objectives")

        # convert old way of doing metric types to new way
        for metric in config["objective"]["metrics"]:
            for member in MetricType:
                if member.value in metric and member.value != "metric":
                    type_ = member.value
                    metric["metric"] = metric.pop(type_)
                    metric["type_"] = type_

        # if weights key is present, then they need to be added to ind metrics
        if "weights" in config["objective"]:
            if len(config["objective"]["weights"]) != len(config["objective"]["metrics"]):
                raise ValueError(
                    "Weights need to be the same length as objectives! " "You must have 1 weight for each objective"
                )
            for metric, weight in zip(config["objective"]["metrics"], config["objective"]["weights"]):
                metric["weight"] = weight
            # delete leftover weights key
            del config["objective"]["weights"]

        #####################################################
        # restructure generation_strategy to streamlined generation_steps format
        if "generation_strategy" in opt_ops:
            config["generation_steps"] = opt_ops["generation_strategy"]["steps"]

        #####################################################
        #  copy over scheduler
        if "scheduler" in opt_ops:
            config["scheduler"] = opt_ops["scheduler"]
        if "trials" in opt_ops:
            if "scheduler" not in config:
                config["scheduler"] = {}
            config["scheduler"]["total_trials"] = opt_ops["trials"]

        #####################################################
        #  copy over experiment name
        if "name" in opt_ops.get("experiment", {}):
            config["name"] = opt_ops["experiment"]["name"]

        return config

    @classmethod
    def from_deprecated(cls, configd: dict):
        return cls(**cls.convert_deprecated(configd=configd))


if __name__ == "__main__":
    from tests.conftest import TEST_CONFIG_DIR

    c = Config.from_jsonlike(pathlib.Path(TEST_CONFIG_DIR / "test_config_generic.yaml"))
