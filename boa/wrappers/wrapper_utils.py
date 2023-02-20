"""
########################
Wrapper Utility Tools
########################

Utility tools for to ease model wrapping.

"""

from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import shlex
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from typing import TYPE_CHECKING, Type, Union

import yaml
from ax.core.base_trial import BaseTrial
from ax.core.parameter import ChoiceParameter, FixedParameter, RangeParameter
from ax.exceptions.core import AxError
from ax.storage.json_store.encoder import object_to_json
from ax.utils.common.docutils import copy_doc

from boa.definitions import IS_WINDOWS, PathLike, PathLike_tup
from boa.logger import get_logger
from boa.utils import (
    _load_attr_from_module,
    _load_module_from_path,
    get_dictionary_from_callable,
)

if TYPE_CHECKING:  # pragma: no cover
    from boa import BaseWrapper

logger = get_logger()


PARAM_CLASSES = {
    "range": RangeParameter,
    "choice": ChoiceParameter,
    "fixed": FixedParameter,
}


@contextmanager
def cd_and_cd_back(path: PathLike = None):
    """Context manager that will return to the starting directory
    when the context manager exits, regardless of what directory
    changes happen between start and end.

    Parameters
    ==========
    path
        If supplied, will change directory to this path at the start of the
        context manager (it will "cd" to this path before "cd" back to the
        original directory)

    Examples
    ========
    >>> starting_dir = os.getcwd()
    ... with cd_and_cd_back():
    ...     # with do some things that change the directory
    ...     os.chdir("..")
    ... # When we exit the context manager (dedent) we go back to the starting directory
    ... ending_dir = os.getcwd()
    ... assert starting_dir == ending_dir

    >>> starting_dir = os.getcwd()
    ... path_to_change_to = ".."
    ... with cd_and_cd_back(path=path_to_change_to):
    ...     # with do some things inside the context manager
    ...     ...
    ... # When we exit the context manager (dedent) we go back to the starting directory
    ... ending_dir = os.getcwd()
    ... assert starting_dir == ending_dir

    """
    cwd = os.getcwd()
    try:
        if path:
            os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


def cd_and_cd_back_dec(path: PathLike = None):
    """Same as :func:`cd_and_cd_back` except as a function decorator instead of
    a context manager.

    Parameters
    ==========
    path
        If supplied, will change directory to this path at the start of the function run
        (it will "cd" to this path before "cd" back to the original directory)

    Examples
    ========
    >>> @cd_and_cd_back_dec
    ... def foo():
    ...     os.chdir("..")
    ...
    ... starting_dir = os.getcwd()
    ... foo()
    ... ending_dir = os.getcwd()
    ... assert starting_dir == ending_dir

    >>> @cd_and_cd_back_dec(path="..")
    ... def bar():
    ...     os.chdir("..")
    ...
    ... starting_dir = os.getcwd()
    ... bar()
    ... ending_dir = os.getcwd()
    ... assert starting_dir == ending_dir

    """

    def _cd_and_cd_back_dec(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with cd_and_cd_back(path):
                return func(*args, **kwargs)

        return wrapper

    return _cd_and_cd_back_dec


def initialize_wrapper(
    wrapper: Type[BaseWrapper] | PathLike,
    append_timestamp: bool = None,
    experiment_dir: PathLike = None,
    wrapper_name: str = "Wrapper",
    post_init_attrs: dict = None,
    **kwargs,
):
    if isinstance(wrapper, PathLike_tup):
        module = _load_module_from_path(wrapper, "user_wrapper")
        WrapperCls: Type[BaseWrapper] = _load_attr_from_module(module, wrapper_name)
    else:
        WrapperCls = wrapper

    if experiment_dir:
        kwargs["experiment_dir"] = experiment_dir
    if append_timestamp is not None:
        kwargs["append_timestamp"] = append_timestamp

    load_config_kwargs = get_dictionary_from_callable(WrapperCls.__init__, kwargs)
    wrapper = WrapperCls(**load_config_kwargs)

    if post_init_attrs:
        for attr_name, value in post_init_attrs.items():
            setattr(wrapper, attr_name, value)
    return wrapper


def split_shell_command(cmd: str):
    """
    split shell command for passing to python subproccess.
    This should correctly split commands like "echo 'Hello, World!'"
    to ['echo', 'Hello, World!'] (2 items) and not ['echo', "'Hello,", "World!'"] (3 items)

    It also works for posix and windows systems appropriately
    """
    return shlex.split(cmd, posix=not IS_WINDOWS)


def load_json(file: PathLike, normalize: bool = True, *args, **kwargs) -> dict:
    """
    Read experiment configuration file for setting up the optimization.
    The configuration file contains the list of parameters, and whether each parameter is a fixed
    parameter or a range parameter. Fixed parameters have a value specified, and range
    parameters have a range specified.

    Parameters
    ----------
    file
        File path for the experiment configuration file
    normalize
        Whether to run :func:`.normalize_config` after loading config
        to run certain predictable configuration normalization. (default true)
    parameter_keys
        Alternative keys or paths to keys to parse  as parameters to optimize,
        for more information, see :func:`.wpr_params_to_boa`

    Examples
    --------

        config_path = Path("path/to/your/config.json_or_yaml")
        config = load_jsonlike(config_path)

    Returns
    -------
    loaded_configs: dict

    See Also
    -------- jmn nmn
    :func:`.normalize_config` for information on ``parameter_keys`` option
    """
    file = pathlib.Path(file).expanduser()
    with open(file, "r") as f:
        config = json.load(f)

    if normalize:
        return normalize_config(config, *args, **kwargs)
    return config


@copy_doc(load_json)
def load_yaml(file: PathLike, normalize: bool = True, *args, **kwargs) -> dict:
    file = pathlib.Path(file).expanduser()
    with open(file, "r") as f:
        config: dict = yaml.safe_load(f)

    if normalize:
        return normalize_config(config, *args, **kwargs)
    return config


@copy_doc(load_json)
def load_jsonlike(file: PathLike, *args, **kwargs):
    file = pathlib.Path(file)
    if file.suffix.lstrip(".").lower() in {"yaml", "yml"}:
        return load_yaml(file, *args, **kwargs)
    elif file.suffix.lstrip(".").lower() == "json":
        return load_json(file, *args, **kwargs)
    else:
        raise ValueError(
            f"Invalid config file format for config file {file}" "\nAccepted file formats are YAML and JSON."
        )


def normalize_config(
    config: dict, parameter_keys: str | list[Union[str, list[str], list[Union[str, int]]]] = None
) -> dict:
    """
    Normalize config dictionary passed in.

    Perform a series of minor convenience normalizations to your configuration dictionary.
    These include adding empty sections for certain optional sections you don't include.
    Defaulting you experiment name to boa_runs if you don't include it.
    And any pathing you include under the parameter_keys section, will get prepended with its
    path, and will get added to your parameters section.

    Instead of putting all of your parameters under the parameters key,
    You can put them under different keys, and then
    pass a list of lists where each list is the json/yaml pathing to the
    additional parameters key section.

    Useful for if you have multiple sections of parameters that you
    want to keep logically separated but you are still optimizing over
    them all, such as different plant species in a multi-species plant model.

    Parameters
    ----------
    config: dict
        your configuration dictionary (jsonlike)
    parameter_keys: str | list[Union[str, list[str], list[Union[str, int]]]]
        This needs to be a json path to a key or keys where parameters or stored. So
        either a single string (the key) or a list of strings and ints (the keys and list indices),
        or a list of those lists for multiple paths.

    Returns
    -------
    config: dict
        normalized configuration

    Examples
    --------
    .. code-block:: yaml

        optimization_options:
            parameter_keys: [
                ["params", "a"],
            ]

            # Alternatively, these keys can be expressed in more traditional YAML
            # syntax, but the above more traditional json like syntax might be easier
            # to understand. They both mean the same thing, a list of lists
            #    -
            #        - "params"
            #        - "a"

        params:
            a:
                x1:
                    type: range
                    bounds: [0, 1]
                x2:
                    type: fixed
                    value: 0.5

        # This would get normalized to

        parameters:
            params_a_x2:
                type: range
                bounds: [0, 1]
            params_a_x1:
                type: fixed
                value: 0.5

    # A more complicated working example
        >>> from boa import normalize_config
        >>> from pprint import pprint
        >>> config = {
        ...     "params": {
        ...         "a": {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}},
        ...         "b": {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}},
        ...     },
        ...     "params2": [
        ...         {0: {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}}},
        ...         {0: {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}}},
        ...     ],
        ...     "params_a": {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}},
        ... }
        >>> parameter_keys = [
        ...     ["params", "a"],
        ...     ["params", "b"],
        ...     ["params_a"],
        ...     ["params2", 0, 0],
        ...     ["params2", 1, 0],
        ... ]
        >>> config = normalize_config(config, parameter_keys)
        >>> pprint(config["parameters"])
        [{'bounds': [0, 1], 'name': 'params_a_x1', 'type': 'range'},
         {'name': 'params_a_x2', 'type': 'fixed', 'value': 0.5},
         {'bounds': [0, 1], 'name': 'params_b_x1', 'type': 'range'},
         {'name': 'params_b_x2', 'type': 'fixed', 'value': 0.5},
         {'bounds': [0, 1], 'name': 'params_a_x1_0', 'type': 'range'},
         {'name': 'params_a_x2_0', 'type': 'fixed', 'value': 0.5},
         {'bounds': [0, 1], 'name': 'params2_0_0_x1', 'type': 'range'},
         {'name': 'params2_0_0_x2', 'type': 'fixed', 'value': 0.5},
         {'bounds': [0, 1], 'name': 'params2_1_0_x1', 'type': 'range'},
         {'name': 'params2_1_0_x2', 'type': 'fixed', 'value': 0.5}]
    """
    config["optimization_options"] = config.get("optimization_options", {})
    for key in ["experiment", "generation_strategy", "scheduler"]:
        config["optimization_options"][key] = config["optimization_options"].get(key, {})
    # Experiment name will default to the "boa_runs" if no name is provided
    config["optimization_options"]["experiment"]["name"] = config["optimization_options"]["experiment"].get(
        "name", "boa_runs"
    )

    if parameter_keys:
        parameters, mapping = wpr_params_to_boa(config, parameter_keys)
        config["parameters"] = parameters
        config["optimization_options"]["mapping"] = mapping

    # Format parameters for Ax experiment
    config["parameters_orig"] = deepcopy(config.get("parameters", {}))
    config["parameter_constraints_orig"] = deepcopy(config.get("parameter_constraints", []))

    parameters = config.get("parameters", {})
    # parameters in the form of name: options, normalize to a list form: [{name: x, bounds: (1, 2), etc}]
    if isinstance(parameters, dict):
        search_space_parameters = []
        for param in config.get("parameters", {}).keys():
            d = deepcopy(config["parameters"][param])
            d["name"] = param  # Add "name" attribute for each parameter
            # remove bounds on fixed params
            if d.get("type", "") == "fixed" and "bounds" in d:
                del d["bounds"]
            # Remove value on range params
            if d.get("type", "") == "range" and "value" in d:
                del d["value"]

            search_space_parameters.append(d)

        config["parameters"] = search_space_parameters

    return config


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

    return new_params, mapping


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


def get_dt_now_as_str(fmt: str = "%Y%m%dT%H%M%S") -> str:
    """get the datetime as now as a str.

    fmt : str
        Default format is file friendly.
        See `strftime documentation <https://docs.python.org/3/library/datetime.html
        #strftime-and-strptime-behavior>`_ for more information on choices.
    """
    return dt.datetime.now().strftime(fmt)


def make_experiment_dir(
    output_dir: PathLike = None,
    experiment_dir: PathLike = None,
    experiment_name: str = "",
    append_timestamp: bool = True,
    exist_ok: bool = False,
    **kwargs,
):
    """
    Creates directory for the experiment and returns the path.
    The directory is named with the experiment name and the current datetime.

    Parameters
    ----------
    output_dir
        Output directory, the parent directory where the experiment directory will be written.
        Specify either an output directory and an experiment name or an experiment_dir
    experiment_dir
        The exact dir the experiment directory boa will use to write the runs to.
        Specify either a output directory and an experiment name or an experiment_dir
    experiment_name
        Name of the experiment
    append_timestamp
        Whether to append a timestamp to the end of the experiment directory
        to ensure uniqueness
    exist_ok
        Whether it is ok if the directory already exists or not
        (will throw an error if set to False and it already exists)

    Returns
    -------
    pathlib.Path
        Path to the directory for the experiment
    """
    if (output_dir and experiment_dir) or (not output_dir and not experiment_dir):
        raise ValueError(
            "`make_experiment_dir` must take either a `output_dir` and `experiment_name` "
            "or an `experiment_dir`, not both and not neither."
        )
    if experiment_dir:
        return _mk_exp_dir_from_exp_dir(exp_dir=experiment_dir, append_timestamp=append_timestamp, exist_ok=exist_ok)
    return _mk_exp_dir_from_output_dir(
        output_dir=output_dir, experiment_name=experiment_name, append_timestamp=append_timestamp, exist_ok=exist_ok
    )


def _mk_exp_dir_from_output_dir(
    output_dir: PathLike, experiment_name: str = "", append_timestamp: bool = True, exist_ok: bool = False
):
    ts = get_dt_now_as_str() if append_timestamp else ""
    exp_name = "_".join(name for name in [experiment_name, ts] if name)
    ex_dir = pathlib.Path(output_dir).expanduser() / exp_name
    ex_dir.mkdir(exist_ok=exist_ok)
    return ex_dir


def _mk_exp_dir_from_exp_dir(exp_dir: PathLike, append_timestamp: bool = True, exist_ok: bool = False):
    exp_dir = pathlib.Path(exp_dir)
    output_dir = exp_dir.parent
    experiment_name = exp_dir.name
    return _mk_exp_dir_from_output_dir(
        output_dir=output_dir, experiment_name=experiment_name, append_timestamp=append_timestamp, exist_ok=exist_ok
    )


def zfilled_trial_index(trial_index: int, fill_size: int = 6) -> str:
    """Return trial index left passed with zeros of length ``fill_size``"""
    return str(trial_index).zfill(fill_size)


def get_trial_dir(experiment_dir: PathLike, trial_index: int, **kwargs):
    """
    Return a directory for a trial,
    Trial directory is named with the trial index (0 padded to 6 decimal)

    Parameters
    ----------
    experiment_dir
        Directory for the experiment
    trial_index
        Trial index from the Ax client
    **kwargs
        keyword args passed to ``zfilled_trial_index``

    Returns
    -------
    pathlib.Path
        Directory for the trial
    """
    trial_dir = pathlib.Path(experiment_dir) / zfilled_trial_index(trial_index, **kwargs)  # zero-padded trial index
    return trial_dir


def make_trial_dir(experiment_dir: PathLike, trial_index: int, exist_ok=True, **kwargs):
    """
    Create a directory for a trial, and return the path to the directory.
    Trial directory is created inside the experiment directory,
    and named with the trial index (0 padded to 6 decimal).
    Model configs and outputs for each trial will be written here.

    Parameters
    ----------
    experiment_dir
        Directory for the experiment
    trial_index
        Trial index from the Ax client
    exist_ok
        Whether it is ok if the directory already exists. Errors if set to False
        and the directory already exists. Sometimes the directory
        already exists if reusing experiment directory of continueing
        stopped experiments that were interrupted and have to restart trials
    **kwargs
        keyword args passed to ``get_trial_dir``

    Returns
    -------
    pathlib.Path
        Directory for the trial
    """
    trial_dir = get_trial_dir(experiment_dir, trial_index, **kwargs)
    trial_dir.mkdir(exist_ok=exist_ok)
    logger.info(f"Trial directory made: {trial_dir}")
    return trial_dir


def save_trial_data(trial: BaseTrial, trial_dir: pathlib.Path = None, experiment_dir: PathLike = None, **kwargs):
    """Save trial data (trial.json, parameters.json and data.json) to
    either: supplied trial_dir or supplied experiment_dir / trial.index
    """

    if not trial_dir:
        trial_dir = get_trial_dir(experiment_dir, trial.index)
        trial_dir.mkdir(parents=True, exist_ok=True)
    kw = {}
    for key, value in kwargs.items():
        try:
            kw[key] = object_to_json(value)
        except (AxError, ValueError) as e:
            kw[key] = str(value)
            logger.warning(e)
    parameters_jsn = object_to_json(trial.arm.parameters)
    trial_jsn = object_to_json(trial)
    data = {
        "parameters": parameters_jsn,
        "trial": trial_jsn,
        "trial_index": trial.index,
        "trial_dir": str(trial_dir),
        **kw,
    }
    for name, jsn in zip(["parameters", "trial", "data"], [parameters_jsn, trial_jsn, data]):
        file_path = trial_dir / f"{name}.json"
        if not file_path.exists():
            with open(file_path, "w+") as file:  # pragma: no cover
                file.write(json.dumps(jsn))
    return trial_dir
