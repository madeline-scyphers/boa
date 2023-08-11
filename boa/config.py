from __future__ import annotations

import copy
import pathlib
from dataclasses import asdict as dc_asdict
from dataclasses import is_dataclass
from enum import Enum
from types import ModuleType
from typing import Any, Callable, ClassVar, Optional, Union

import ax.early_stopping.strategies as early_stopping_strats
import ax.global_stopping.strategies as global_stopping_strats
from attr import asdict
from attrs import Factory, converters, define, field, fields, fields_dict
from ax.modelbridge.generation_node import GenerationStep
from ax.modelbridge.registry import Models
from ax.service.scheduler import SchedulerOptions
from ax.service.utils.instantiation import TParameterRepresentation

from boa.definitions import PathLike
from boa.utils import deprecation
from boa.wrappers.wrapper_utils import load_jsonlike

__all__ = ["BOAObjective", "BOAMetric", "MetricType", "BOAScriptOptions", "BOAConfig"]


@define
class ToDict:
    _filtered_dict_fields: ClassVar[str] = None

    def to_dict(self):
        def vs(inst, attrib, val):
            if is_dataclass(val):
                return dc_asdict(val)
            return val

        return {
            "__type": self.__class__.__name__,
            **asdict(
                self,
                filter=lambda attr, value: True
                if not self._filtered_dict_fields
                else attr.name not in self._filtered_dict_fields,
                value_serializer=vs,
            ),
        }


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


class MetricType(str, Enum):
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
class BOAMetric(ToDict):
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


def _metric_converter(ls: list[BOAMetric | dict]) -> list[BOAMetric]:
    for i, metric in enumerate(ls):
        if isinstance(metric, dict):
            ls[i] = BOAMetric(**metric)
    return ls


@define
class BOAObjective(ToDict):
    metrics: list[BOAMetric] = field(converter=_metric_converter)
    outcome_constraints: Optional[list[str]] = Factory(list)
    objective_thresholds: Optional[list[str]] = Factory(list)
    minimize: Optional[bool] = None


@define
class BOAScriptOptions(ToDict):
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
                    "Must specify path to config directory in `BOAScriptOptions` dataclass when using rel-to-config"
                    "as the `base_path` argument."
                    "If you are an external user, the easiest way to ensure this, is to use the Config.from_jsonlike"
                    "class constructor, with either `rel_to_config` set to true in the config file or rel_to_config"
                    "set to true as an argument (to override what is in the config). This will automatically set "
                    "the `base_path` argument for `BOAScriptOptions`."
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


obj_comment = "this is a test"


@define(kw_only=True)
class BOAConfig(ToDict):
    """Base doc string"""

    objective: dict | BOAObjective = field(
        converter=_convert_noton_type(lambda d: BOAObjective(**d), type_=BOAObjective),
        metadata={"annotation": "First metadata test"},
    )
    # """objective docstring"""
    parameters: dict[str, dict] | list[TParameterRepresentation] = field(
        converter=_parameter_normalization, metadata={"doc": "this is a second test"}
    )  #
    generation_steps: Optional[list[dict] | list[GenerationStep]] = field(
        default=None,
        converter=converters.optional(_gen_step_converter),
        metadata={"doc": "When manually setting steps to generate new trials"},
    )
    scheduler: Optional[dict | SchedulerOptions] = field(
        default=None,
        converter=_convert_noton_type(_scheduler_converter, type_=SchedulerOptions, default_if_none=SchedulerOptions),
    )
    # this is a regular comment test
    name: str = "boa_runs"
    parameter_constraints: list[str] = Factory(list)  #
    model_options: Optional[dict | list] = None  #
    script_options: Optional[dict | BOAScriptOptions] = field(
        default=None,
        converter=_convert_noton_type(
            lambda d: BOAScriptOptions(**d), type_=BOAScriptOptions, default_if_none=BOAScriptOptions
        ),
    )
    parameter_keys: Optional[str | list[Union[str, list[str], list[Union[str, int]]]]] = None

    config_path: Optional[PathLike] = None
    n_trials: Optional[int] = None
    total_trials: Optional[int] = None
    mapping: Optional[dict[str, str]] = field(init=False)
    # we don't use this key for eq checks because with serialize and deserialize, it then gets all
    # default options as well
    orig_config: dict = field(init=False, eq=False)

    _filtered_dict_fields: ClassVar[str] = ["mapping", "orig_config"]

    def __init__(self, parameter_keys=None, n_trials=None, total_trials=None, **config):
        if total_trials and n_trials:
            raise TypeError("You can specify either n_trials or total_trials, but not both")
        if total_trials:
            if "scheduler" not in config:
                config["scheduler"] = {}
            config["scheduler"]["total_trials"] = total_trials
        elif n_trials:
            if "scheduler" in config:
                config["scheduler"].pop("total_trials", None)
        self.orig_config = copy.deepcopy(config)

        # we instantiate it as None since all defined attributes from above need to exist
        self.mapping = None
        if parameter_keys:
            parameters, mapping = self.wpr_params_to_boa(config, parameter_keys)
            config["parameters"] = parameters
            self.mapping = mapping
        self.__attrs_init__(**config, parameter_keys=parameter_keys, total_trials=total_trials, n_trials=n_trials)

    @classmethod
    def from_jsonlike(cls, file, rel_to_config: Optional[bool] = None):
        config_path = pathlib.Path(file).resolve()
        config = load_jsonlike(config_path, normalize=False)

        config = cls.convert_deprecated(configd=config)

        script_options = config.get("script_options") or {}
        rel_to_config = rel_to_config or script_options.get(
            "rel_to_config", fields_dict(BOAScriptOptions)["rel_to_config"].default
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
        if "trials" in opt_ops or "n_trials" in opt_ops:
            config["n_trials"] = opt_ops.get("n_trials") or opt_ops.get("trials")

        #####################################################
        #  copy over experiment name
        if "name" in opt_ops.get("experiment", {}):
            config["name"] = opt_ops["experiment"]["name"]

        return config

    @classmethod
    def from_deprecated(cls, configd: dict):
        return cls(**cls.convert_deprecated(configd=configd))

    @property
    def trials(self):
        return self.n_trials or self.total_trials or self.scheduler.total_trials

    @staticmethod
    def wpr_params_to_boa(
        params: dict, parameter_keys: str | list[Union[str, list[str], list[Union[str, int]]]]
    ) -> tuple[dict, dict]:
        """

        Parameters
        ----------
        params
            dictionary containing parameters
        parameter_keys
            str of key to parameters, or list of json paths to key(s) of parameters.
        """
        # if only one key is passed in as a str, wrap it in a list
        if isinstance(parameter_keys, str):
            parameter_keys = [parameter_keys]

        new_params = {}
        mapping = {}
        for maybe_key in parameter_keys:
            path_type = []
            if isinstance(maybe_key, str):
                key = maybe_key
                d = params[key]
            elif isinstance(maybe_key, (list, tuple)):
                d = params[maybe_key[0]]
                if len(maybe_key) > 1:
                    for k in maybe_key[1:]:
                        if isinstance(d, dict):
                            path_type.append("dict")
                        else:
                            path_type.append("list")
                        d = d[k]
                path_type.append("dict")  # the last key is always a dict to the param info

                key = "_".join(str(k) for k in maybe_key)
            else:
                raise TypeError(
                    "wpr_params_to_boa accepts str, a list of str, or a list of lists of str "
                    "\nfor the keys (or paths of keys) to the AX parameters you wish to prepend."
                )
            for parameter_name, dct in d.items():
                new_key = f"{key}_{parameter_name}"
                key_index = 0
                while new_key in new_params:
                    new_key += f"_{key_index}"
                    if new_key in new_params:
                        key_index += 1
                        new_key = new_key[:-2]
                new_params[new_key] = dct
                mapping[new_key] = dict(path=maybe_key, original_name=parameter_name, path_type=path_type)
        for mapped, info in mapping.items():  # remove all old keys
            params.pop(info["path"][0], None)
        return new_params, mapping

    @staticmethod
    def boa_params_to_wpr(params: list[dict], mapping, from_trial=True):
        new_params = {}
        for parameter in params:
            if from_trial:
                name = parameter
            else:
                name = parameter["name"]
            path = mapping[name]["path"]
            original_name = mapping[name]["original_name"]
            path_type = mapping[name]["path_type"]

            p1 = path[0]
            pt1 = path_type[0]

            if path[0] not in new_params:
                if pt1 == "dict":
                    new_params[p1] = {}
                else:
                    new_params[p1] = []

            d = new_params[p1]
            if len(path) > 1:
                for key, typ in zip(path[1:], path_type[1:]):
                    if (isinstance(d, list) and key + 1 > len(d)) or (isinstance(d, dict) and key not in d):
                        if isinstance(d, list):
                            d.extend([None for _ in range(key + 1 - len(d))])
                        if typ == "dict":
                            d[key] = {}
                        else:
                            d[key] = []
                    d = d[key]
            if from_trial:
                d[original_name] = params[parameter]
            else:
                d[original_name] = {k: v for k, v in parameter.items() if k != "name"}

        return new_params


nl = "\n"
BOAConfig.__doc__ = BOAConfig.__doc__ + "".join(f'{nl}{f.metadata.get("doc", "")}' for f in fields(BOAConfig))


if __name__ == "__main__":
    from tests.conftest import TEST_CONFIG_DIR

    c = BOAConfig.from_jsonlike(pathlib.Path(TEST_CONFIG_DIR / "test_config_generic.yaml"))

    # import ruamel.yaml
    # import ruamel.yaml.comments
    #
    # yaml = ruamel.yaml.YAML()  # defaults to round-trip
    # with open(pathlib.Path(TEST_CONFIG_DIR / "test_config_generic.yaml", "r")) as f:
    #     data: ruamel.yaml.comments.CommentedMap = yaml.load(f)
    # data.yaml_add_eol_comment
