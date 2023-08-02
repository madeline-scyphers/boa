from __future__ import annotations

import os
import pathlib
from types import ModuleType
from typing import Optional

import ax.early_stopping.strategies as early_stopping_strats
import ax.global_stopping.strategies as global_stopping_strats
from attrs import Factory, define, field
from ax.modelbridge.generation_node import GenerationStep
from ax.modelbridge.registry import Models
from ax.service.scheduler import SchedulerOptions
from ax.service.utils.instantiation import TParameterRepresentation

from boa.definitions import PathLike
from boa.wrappers.wrapper_utils import load_jsonlike


@define
class Objective:
    name: str
    metric: str
    noise_sd: Optional[float] = 0
    minimize: Optional[bool] = True
    info_only: bool = False
    weight: Optional[float] = None
    properties: Optional[dict] = None


@define
class ScriptOptions:
    rel_to_config: Optional[bool] = None
    rel_to_launch: Optional[bool] = True
    base_path: Optional[PathLike] = field(factory=os.getcwd, converter=pathlib.Path)
    wrapper_name: str = "Wrapper"
    append_timestamp: bool = True
    wrapper_path: str = "wrapper.py"
    working_dir: str = "."
    experiment_dir: str = "experiment_dir"

    def __attrs_post_init__(self):
        if (self.rel_to_config and self.rel_to_launch) or (not self.rel_to_config and not self.rel_to_launch):
            raise TypeError("Must specify exactly one of rel_to_here or rel_to_config")

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


def _gen_step_converter(steps: Optional[list]) -> list[GenerationStep]:
    for step in steps:
        try:
            step["model"] = Models[step["model"]]
        except KeyError:
            step["model"] = Models(step["model"])
    return [GenerationStep(**step) for step in steps]


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
class Config:
    objectives: list[Objective] = field(converter=lambda ls: [Objective(**obj) for obj in ls])
    parameters: list[TParameterRepresentation] = field(converter=_parameter_normalization)
    outcome_constraints: list[str] = None
    objective_thresholds: list[str] = None
    generation_steps: Optional[list[GenerationStep]] = field(default=None, converter=_gen_step_converter)
    scheduler: Optional[SchedulerOptions] = field(default=None, converter=_scheduler_converter)
    name: str = "boa_runs"
    parameter_constraints: list[str] = Factory(list)
    model_options: Optional[dict | list] = None
    script_options: Optional[ScriptOptions] = field(default=None, converter=ScriptOptions)

    @classmethod
    def from_jsonlike(cls, file):
        config_path = pathlib.Path(file).resolve()
        config = load_jsonlike(config_path, normalize=False)
        return cls(**config)

    # @classmethod
    # def generate_default_config(cls):
    #     ...


if __name__ == "__main__":
    from tests.conftest import TEST_CONFIG_DIR

    config = Config.from_jsonlike(pathlib.Path(TEST_CONFIG_DIR / "test_config_generic.yaml"))
