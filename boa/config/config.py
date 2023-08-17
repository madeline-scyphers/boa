from __future__ import annotations

import copy
import pathlib
from dataclasses import asdict as dc_asdict
from dataclasses import is_dataclass
from enum import Enum
from typing import ClassVar, Optional, Union

import attr
import ruamel.yaml
import ruamel.yaml.comments
from attr import asdict
from attrs import Factory, converters, define, field, fields_dict
from ax.service.utils.instantiation import TParameterRepresentation
from ax.service.utils.scheduler_options import SchedulerOptions
from ax.storage.json_store.encoder import object_to_json
from ax.utils.common.base import Base as AxBase

from boa.config.converters import (
    _convert_noton_type,
    _gen_strat_converter,
    _metric_converter,
    _parameter_normalization,
    _scheduler_converter,
)
from boa.definitions import PathLike
from boa.utils import StrEnum, deprecation
from boa.wrappers.wrapper_utils import load_jsonlike

__all__ = [
    "BOAConfig",
    "BOAObjective",
    "BOAScriptOptions",
    "BOAMetric",
    "MetricType",
    # "SchedulerOptions",
    # "GenerationStep",
]


NL = "\n"


@define
class _Utils:
    _filtered_dict_fields: ClassVar[list[str]] = None

    def to_dict(self) -> dict:
        def vs(inst, attrib, val):
            if is_dataclass(val):
                return dc_asdict(val)
            elif not attr.has(val) and hasattr(val, "to_dict"):
                return val.to_dict()
            elif isinstance(val, Enum):
                return val.value
            elif isinstance(val, pathlib.Path):
                return str(val)
            elif isinstance(val, AxBase):
                return object_to_json(val)
            return val

        def remove_type_recurse(d):
            if isinstance(d, dict):
                return {k: remove_type_recurse(v) for k, v in d.items() if k != "__type"}
            elif isinstance(d, list):
                return [remove_type_recurse(v) for v in d]
            return d

        # d = object_to_json(self)
        # if not add_type:
        #     return remove_type_recurse(d)
        # return d

        d = {
            **asdict(
                self,
                filter=lambda attr, value: True
                if not self._filtered_dict_fields
                else attr.name not in (self._filtered_dict_fields + ["_generating_default_doc_config"]),
                value_serializer=vs,
            ),
        }

        return remove_type_recurse(d)


class MetricType(StrEnum):
    METRIC = "metric"
    BOA_METRIC = "boa_metric"
    SKLEARN_METRIC = "sklearn_metric"
    SYNTHETIC_METRIC = "synthetic_metric"
    PASSTHROUGH = "pass_through"


@define(kw_only=True)
class BOAMetric(_Utils):
    metric: Optional[str] = field(
        default=None,
        metadata={
            "doc": """metrics to be used for optimization. You can use list any metric in built into BOA.
            Those metrics can be found here: :mod:`Metrics <boa.metrics.metrics>`.
            If no metric is specified, a :class:`pass through<.PassThrough>` metric will be used.
            Which means that the metric will be computed by the user and passed to BOA.
            You can also use any metric from sklearn by passing in the name of the metric
            and metric type as `sklearn_metric`.
            You can also use any metric from the Ax's or BoTorch's synthetic metrics modules by
            passing in the name of the metric and metric type as `synthetic_metric`."""
        },
    )
    name: Optional[str] = field(
        default=None,
        converter=converters.optional(str),
        metadata={"doc": "Name of the metric. This is used to identify the metric in your wrapper script."},
    )
    metric_type: Optional[MetricType | str] = field(
        default=MetricType.METRIC,
        converter=converters.optional(MetricType.from_str_or_enum),
        metadata={
            "doc": """Type of metric. In built BOA metrics are of type `metric`,
            by using `sklearn_metric` you can use any metric from sklearn.metrics module,
            by using `synthetic_metric` you can use any synthetic function from Ax's or BoTorch's
            synthetic metrics modules.
            You can also specify `pass_through` to use a metric that is computed by the user."""
        },
    )
    noise_sd: Optional[float] = field(
        default=0,
        metadata={
            "doc": """Standard deviation of the noise to be added to the metric.
            This is useful when you want to simulate noisy metrics.
            If None, interpret the function as noisy with unknown noise level.
            Defaults to `0` (noiseless)."""
        },
    )
    minimize: Optional[bool] = field(
        default=True,
        metadata={
            "doc": """Whether to minimize or maximize the metric.
            Defaults to `True` (minimize) for a general metric,
            but every in built metric in BOA (Mean, RMSE, etc.) has its own default value."""
        },
    )
    info_only: bool = field(
        default=False,
        metadata={
            "doc": """Whether the metric is only used for information purposes only but will still be reported.
            This means that the metric will not be used for optimization. """
        },
    )
    weight: Optional[float] = field(
        default=None,
        metadata={
            "doc": """Weight of the metric. Used in scalarized optimization, which is combining multiple metrics
            into one metric. Scalarized optimization is a way to cheat a multi-objective optimization
            problem into a single objective optimization problem and significantly reduce the computational
            cost."""
        },
    )
    properties: Optional[dict] = field(
        default=None,
        metadata={
            "doc": """Arbitrary properties of the metric. This is used to pass additional information about the metric
            to your wrapper. You can pass whatever information you want to your wrapper and use it in your
            wrapper functions."""
        },
    )

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
            self.metric_type = MetricType.PASSTHROUGH


@define
class BOAObjective(_Utils):
    """
    Your objective to be optimized by BOA.
    This can be a single objective, scalarized objective, or a multi-objective (pareto objective).
    For a single objective, list a single metric in the metrics field.
    For a multi-objective, list multiple metrics in the metrics field.
    For a scalarized objective, list multiple metrics in the metrics field and specify the
    weights for each metric in each metrics weight field.
    """

    metrics: list[BOAMetric] = field(
        converter=_metric_converter,
        metadata={"doc": "A list of BOAMetric objects that represent the metrics to be used in the objective."},
    )
    outcome_constraints: Optional[list[str]] = field(
        factory=list,
        metadata={
            "doc": """String representation of outcome constraint of metrics.
            This bounds a metric (or linear combination of metrics)
            by some bound (>= or <=).
            (ex. ['metric1 >= 0.0', 'metric2 <= 1.0', '2*metric1 + .5*metric2 <= 1.0'])"""
        },
    )
    objective_thresholds: Optional[list[str]] = field(
        factory=list,
        metadata={
            "doc": """String representation of Objective Thresholds for multi-objective optimization.
            An objective threshold represents the threshold for an objective metric
            to contribute to hypervolume calculations. A list containing the objective
            threshold for each metric collectively form a reference point.
            Because the objective thresholds are used to calculate hypervolume, they
            can only be used for multi-objective optimization.
            (ex. ['metric1 >= 0.0', 'metric2 <= 1.0'])"""
        },
    )
    minimize: Optional[bool] = field(
        default=None,
        metadata={
            "doc": """A boolean that indicates whether the scalarized objective should be minimized or maximized.
            Only used for scalarized objectives because each metric can have its own minimize flag.
            Will be ignored for non scalarized objectives."""
        },
    )


@define
class BOAScriptOptions(_Utils):
    rel_to_config: Optional[bool] = field(
        default=True,
        metadata={
            "doc": """Whether to use the config file as the base path for all relative paths.
            If True, all relative paths will be relative to the config file directory.
            Defaults to True if not specified.
            If launched through BOA CLI, this will be set to True automatically.
            rel_to_config and rel_to_launch cannot both be specified."""
        },
    )
    rel_to_launch: Optional[bool] = field(
        default=None,
        metadata={
            "doc": """Whether to use the CLI launch directory as the base path for all relative paths.
            If True, all relative paths will be relative to the CLI launch directory.
            Defaults to `rel_to_config` argument if not specified.
            rel_to_config and rel_to_launch cannot both be specified."""
        },
    )
    wrapper_name: str = field(
        default="Wrapper",
        metadata={
            "doc": """Name of the python wrapper class. Used for python interface only.
            Defaults to `Wrapper` if not specified."""
        },
    )
    wrapper_path: str = field(
        default="wrapper.py",
        metadata={
            "doc": """Path to the python wrapper file. Used for python interface only.
            Defaults to `wrapper.py` if not specified. """
        },
    )
    working_dir: str = field(
        default=".",
        metadata={
            "doc": """Path to the working directory. Defaults to `.` (Current working directory) if not specified. """
        },
    )
    experiment_dir: Optional[PathLike] = field(
        default=None,
        metadata={
            "doc": """Path to the directory for the output of the experiment
            You may specify this or output_dir in your configuration file instead."""
        },
    )
    output_dir: Optional[PathLike] = field(
        default=None,
        metadata={
            "doc": """Output directory of project,
            If you specify output_dir, then output will be saved in
            output_dir / experiment_name
            Because of this only either experiment_dir or output_dir may be specified.
            (if neither experiment_dir nor output_dir are specified, output_dir defaults
            to whatever pwd returns (and equivalent on windows))"""
        },
    )
    append_timestamp: bool = field(
        default=True,
        metadata={
            "doc": """Whether to append a timestamp to the output directory to ensure uniqueness.
            Defaults to `True` if not specified. """
        },
    )
    run_model: Optional[str] = field(
        default=None,
        metadata={
            "doc": """Shell command to run the model. Used for the language-agnostic interface only.
            this is what BOA will do to launch your script.
            it will also pass as a command line argument the current trial directory
            that is be parameterized by BOA.
            `run_model` is the only needed shell command of these 4, because you
            can use it also to write your config, run your model, set your trial status,
            and fetch your trial data all in one script if you so choose. The
            other scripts are provided as a convenience to segment out your logic.
            This can either be a relative path or absolute path. """
        },
    )
    write_configs: Optional[str] = field(
        default=None,
        metadata={"doc": "Shell command to write your configs out. See `run_model` for more details. "},
    )
    set_trial_status: Optional[str] = field(
        default=None,
        metadata={"doc": "Shell command to set your trial status. See `run_model` for more details. "},
    )
    fetch_trial_data: Optional[str] = field(
        default=None,
        metadata={"doc": "Shell command to fetch your trial data. See `run_model` for more details. "},
    )
    base_path: Optional[PathLike] = field(
        default=".",
    )

    def __attrs_post_init__(self):
        if (self.rel_to_config and self.rel_to_launch) or (not self.rel_to_config and not self.rel_to_launch):
            raise TypeError("Must specify exactly one of rel_to_here or rel_to_config")

        if not self.base_path:
            if self.rel_to_config:
                raise TypeError(
                    "Must specify path to config directory in `BOAScriptOptions` dataclass when using rel-to-config"
                    " as the `base_path` argument."
                    " If you are an external user, the easiest way to ensure this, is to use the Config.from_jsonlike"
                    " class constructor, with either `rel_to_config` set to true in the config file or rel_to_config"
                    " set to true as an argument (to override what is in the config). This will automatically set "
                    " the `base_path` argument for `BOAScriptOptions`."
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


@define(kw_only=True)
class BOAConfig(_Utils):
    """Base doc string"""

    objective: dict | BOAObjective = field(
        converter=_convert_noton_type(lambda d: BOAObjective(**d), type_=BOAObjective),
        metadata={
            "default_doc": dict(metrics=[dict(name="metric1", metric="RMSE")]),
            "doc": BOAObjective.__doc__,
        },
    )

    parameters: dict[str, dict] | list[TParameterRepresentation] = field(
        converter=_parameter_normalization,
        metadata={
            "default_doc": {
                "x1": {"type": "range", "bounds": [0, 1], "value_type": "float"},
                "x2": {"type": "choice", "values": ["a", "b", "c"]},
                "x3": 4.0,
            },
            "doc": """
Parameters to optimize over. This can be expressed in two ways. The first is a list of dictionaries, where each
dictionary represents a parameter. The second is a dictionary of dictionaries, where the key is the name of the
parameter and the value is the dictionary representing the parameter.

.. code-block:: yaml

    ## Dictionary of dictionaries
    x1:
        type: range
        bounds: [0, 1]
        value_type: float
    x2:
        type: range
        bounds: [0.0, 1.0]  # value_type is inferred from bounds

.. code-block:: yaml

    ## List of dictionaries 
    -   name: x1
        type: range
        bounds: [0, 1]
        value_type: float

.. code-block:: yaml    


    ## Fixed Types 
    x3: 4.0  # Fixed type, value is 4.0
    x4:
        type: fixed
        value: "some string"  # Fixed type, value is "some string"

    ## Choice Options 
    x5:
        type: choice
        values: ["a", "b"]
""",  # noqa: W291
        },
    )
    generation_strategy: Optional[dict] = field(
        factory=dict,
        converter=_gen_strat_converter,
        metadata={
            "doc": """
Your generation strategy is how new trials will be generated, that is, what acquisition function
will be used to select the next trial, what kernel will be used to model the objective function,
as well as other options such as max parallelism.

This is an optional section. If not specified, Ax will choose a generation strategy for you.
Based on your objective, parameters, and other options. You can pass options to how Ax chooses
a generation strategy by passing options under `generation_strategy`.

See https://ax.dev/tutorials/generation_strategy.html and 
https://ax.dev/api/modelbridge.html#ax.modelbridge.dispatch_utils.choose_generation_strategy 
For specific options. 

If you want to specify your own generation strategy, you can do so by passing a list of
steps under `generation_strategy.steps`

.. code-block:: yaml

    generation_strategy:
        # Use Ax's SAASBO algorithm, which is particularly well suited for high dimensional problems
        use_saasbo: true
        max_parallelism_cap: 10  # Maximum number of trials allowed to run in parallel

Other options are possible, 
see https://ax.dev/tutorials/generation_strategy.html#1A.-Manually-configured-generation-strategy
and Models from ax.modelbridge.registry.py for more options
Some options include SOBOL, GPEI, Thompson, GPKG (knowledge gradient), and others.
See https://ax.dev/api/modelbridge.html#ax.modelbridge.generation_node.GenerationStep
For specific options you can pass to each step

.. code-block:: yaml

    generation_strategy:
    steps:
        -   model: SOBOL
            num_trials: 20
        -   model: GPEI  # Gaussian Process with Expected Improvement
            num_trials: -1
            max_parallelism: 10  # Maximum number of trials allowed to run in parallel
"""  # noqa: W291
        },
    )
    scheduler: Optional[dict | SchedulerOptions] = field(
        default=None,
        converter=_convert_noton_type(_scheduler_converter, type_=SchedulerOptions, default_if_none=SchedulerOptions),
        metadata={
            "default_doc": dict(n_trials=100),
            "doc": SchedulerOptions.__doc__
            + (
                """
        n_trials: Only run this many trials,
            in contrast to `total_trials` which is a hard limit, even after reloading the
            scheduler, this will run n_trials trials every time you reload the scheduler.
            Making it easier to use when reloading the scheduler and continuing to run trials.
"""
            ),
        },
    )
    name: str = "boa_runs"
    parameter_constraints: list[str] = Factory(list)
    model_options: Optional[dict | list] = None
    script_options: Optional[dict | BOAScriptOptions] = field(
        default=None,
        converter=_convert_noton_type(
            lambda d: BOAScriptOptions(**d), type_=BOAScriptOptions, default_if_none=BOAScriptOptions
        ),
    )
    parameter_keys: Optional[str | list[Union[str, list[str], list[Union[str, int]]]]] = None

    config_path: Optional[PathLike] = None
    n_trials: Optional[int] = None
    mapping: Optional[dict[str, str]] = field(init=False)
    # we don't use this key for eq checks because with serialize and deserialize, it then gets all
    # default options as well
    orig_config: dict = field(init=False, eq=False)

    _filtered_dict_fields: ClassVar[str] = ["mapping", "orig_config"]

    def __init__(self, parameter_keys=None, **config):
        scheduler = config.get("scheduler", {})
        n_trials = config.get("n_trials", None)
        if isinstance(scheduler, dict):
            n_trials = scheduler.pop("n_trials", n_trials)  # n_trials is not a valid scheduler option so we pop it
            total_trials = scheduler.get("total_trials", None)
        else:
            total_trials = scheduler.total_trials
        if total_trials and n_trials:
            raise TypeError("You can specify either n_trials or total_trials, but not both")
        if not total_trials and not n_trials:
            raise TypeError("You must specify either n_trials or total_trials")
        if n_trials:
            config["n_trials"] = n_trials
            if "scheduler" in config:
                if isinstance(config["scheduler"], dict):
                    config["scheduler"].pop("total_trials", None)
                elif isinstance(config["scheduler"], SchedulerOptions):
                    if config["scheduler"].total_trials is not None:
                        d = dc_asdict(config["scheduler"])
                        d.pop("total_trials", None)
                        config["scheduler"] = SchedulerOptions(**d)
                else:
                    raise TypeError(f"Scheduler must be a dict or SchedulerOptions, but is {type(config['scheduler'])}")
        self.orig_config = copy.deepcopy(config)

        # we instantiate it as None since all defined attributes from above need to exist
        self.mapping = None
        if parameter_keys:
            parameters, mapping = self.wpr_params_to_boa(config, parameter_keys)
            config["parameters"] = parameters
            self.mapping = mapping
        self.__attrs_init__(**config, parameter_keys=parameter_keys)

    @classmethod
    def from_jsonlike(cls, file, rel_to_config: Optional[bool] = None):
        config_path = pathlib.Path(file).resolve()
        config = load_jsonlike(config_path)

        config = cls.convert_deprecated(configd=config)

        script_options = config.get("script_options") or {}
        rel_to_config = rel_to_config or script_options.get(
            "rel_to_config", fields_dict(BOAScriptOptions)["rel_to_config"].default
        )
        if rel_to_config:
            if not config.get("script_options"):
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
                    metric_type = member.value
                    metric["metric"] = metric.pop(metric_type)
                    metric["metric_type"] = metric_type

        # if weights key is present, then they need to be added to ind metrics
        if "weights" in config["objective"]:
            if len(config["objective"]["weights"]) != len(config["objective"]["metrics"]):
                raise ValueError(
                    "Weights need to be the same length as objectives! You must have 1 weight for each objective"
                )
            for metric, weight in zip(config["objective"]["metrics"], config["objective"]["weights"]):
                metric["weight"] = weight
            # delete leftover weights key
            del config["objective"]["weights"]

        #####################################################
        # copy over generation strategy
        if "generation_strategy" in opt_ops:
            config["generation_strategy"] = opt_ops["generation_strategy"]

        #####################################################
        #  copy over scheduler
        if "scheduler" in opt_ops:
            config["scheduler"] = opt_ops["scheduler"]
        if "trials" in opt_ops or "n_trials" in opt_ops:
            if "scheduler" not in config:
                config["scheduler"] = {}
            config["scheduler"]["n_trials"] = opt_ops.get("n_trials") or opt_ops.get("trials")

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
        return self.n_trials or self.scheduler.total_trials

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


def strip_white_space(s: str):
    return NL.join(ln.strip() for ln in s.splitlines())


def generate_default_doc_config():

    config = BOAConfig(
        **{
            k: copy.deepcopy(v.metadata.get("default_doc"))
            for k, v in fields_dict(BOAConfig).items()
            if v.metadata.get("default_doc")
        }
    )
    d = config.to_dict()

    def set_metadata_default_doc_recurse(d: dict, config):
        for name, attribute in d.items():
            if attr.has(config) and (
                (fields := fields_dict(type(config))) and fields[name].metadata.get("default_doc")
            ):
                if isinstance(d[name], dict):
                    dd = copy.deepcopy(fields[name].metadata["default_doc"])
                    for k, v in d[name].items():
                        if k in dd:
                            d[name][k] = dd[k]
                        else:
                            d[name][k] = "..."
                elif isinstance(d[name], list):
                    d[name] = fields[name].metadata["default_doc"]
            else:
                if isinstance(d[name], dict):
                    d[name] = set_metadata_default_doc_recurse(d[name], getattr(config, name))
                elif isinstance(d[name], list):
                    for i, item in enumerate(d[name]):
                        if isinstance(item, dict):
                            d[name][i] = set_metadata_default_doc_recurse(item, getattr(config, name))
                else:
                    d[name] = "..."

        return d

    d = set_metadata_default_doc_recurse(d, config)

    return d, config


def add_comment_recurse(d: ruamel.yaml.comments.CommentedMap, config=None, where="before", depth=0, indent=2):
    fields = fields_dict(type(config)) if attr.has(config) else {}
    if isinstance(d, dict):
        for key in d:
            if key in fields:
                doc = fields[key].metadata.get("doc")
                if depth == 0:
                    intro = "\n##" + "#" * len(key) + "\n" + key + " #\n" + "#" * len(key) + "##"
                    doc = intro + "\n" + doc if doc else intro
                if doc:
                    doc = strip_white_space(doc)

                    if where == "end" and len(doc.splitlines()) == 1:
                        d.yaml_add_eol_comment(comment=doc, key=key)
                    elif where == "before" or where == "end":
                        d.yaml_set_comment_before_after_key(key=key, before=doc, indent=indent * depth)
                    else:
                        raise ValueError("where must be 'before' or 'end'")

                d[key] = add_comment_recurse(d[key], getattr(config, key), depth=depth + 1, indent=indent)
    elif isinstance(d, list):
        for (i, item), new_config in zip(enumerate(d), config):
            if isinstance(item, dict):
                d[i] = add_comment_recurse(item, new_config, where="end", depth=depth + 1, indent=indent)

    return d


if __name__ == "__main__":
    from tests.conftest import TEST_CONFIG_DIR

    c = BOAConfig.from_jsonlike(pathlib.Path(TEST_CONFIG_DIR / "test_config_generic.yaml"))
