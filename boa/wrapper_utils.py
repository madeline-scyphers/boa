"""
Optimization wrapper for FETCH3.

These functions provide the interface between the optimization tool and FETCH3
- Setting up optimization experiment
- Creating directories for model outputs of each iteration
- Writing model configuration files for each iteration
- Starting model runs for each iteration
- Reading model outputs and observation data for model evaluation
- Defines objective function for optimization, and other performance metrics of interest
- Defines how results of each iteration should be evaluated
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import os
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from pathlib import Path
from typing import Union

import yaml
from ax.core.parameter import ChoiceParameter, FixedParameter, RangeParameter
from ax.utils.common.docutils import copy_doc

logger = logging.getLogger(__file__)


PARAM_CLASSES = {
    "range": RangeParameter,
    "choice": ChoiceParameter,
    "fixed": FixedParameter,
}


@contextmanager
def cd_and_cd_back(path=None):
    cwd = os.getcwd()
    try:
        if path:
            os.chdir(path)
        yield
    finally:
        os.chdir(cwd)


def cd_and_cd_back_dec(path=None):
    def _cd_and_cd_back_dec(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with cd_and_cd_back(path):
                return func(*args, **kwargs)

        return wrapper

    return _cd_and_cd_back_dec


def load_jsonlike(file_path: os.PathLike, normalize: bool = True, *args, **kwargs):
    """
    Read experiment configuration file for setting up the optimization.
    yml file contains the list of parameters, and whether each parameter is a fixed
    parameter or a range parameter. Fixed parameters have a value specified, and range
    parameters have a range specified.

    Parameters
    ----------
    config_file : os.PathLike
        File path for the experiment configuration file
    normalize : bool
        Whether to run boa.wrapper_utils.normalize_config after loading config
        to run certain predictable configuration normalization. (default true)
    parameter_keys : str | list[Union[str, list[str], list[Union[str, int]]]]
        Alternative keys or paths to keys to parse  as parameters to optimize,
        for more information, see :func:`~boa.wrapper_utils.wpr_params_to_boa`


    Examples
    --------
    If you have a parameters in your configration like this

    >>> from boa import normalize_config
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
     ...    ["params2", 1, 0],
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

    Returns
    -------
    loaded_configs: dict
    """
    file_path = Path(file_path).expanduser()
    with open(file_path, "r") as f:
        if file_path.suffix.lstrip(".").lower() in {"yaml", "yml"}:
            config = yaml.safe_load(f)
        elif file_path.suffix.lstrip(".").lower() == "json":
            config = json.load(f)
        else:
            raise ValueError(
                f"Invalid config file format for config file {file_path}" "\nAccepted file formats are YAML and JSON."
            )

    if normalize:
        return normalize_config(config, *args, **kwargs)
    return config


@copy_doc(load_jsonlike)
def load_json(*args, **kwargs) -> dict:
    return load_jsonlike(*args, **kwargs)


@copy_doc(load_jsonlike)
def load_yaml(*args, **kwargs) -> dict:
    return load_jsonlike(*args, **kwargs)


def normalize_config(
    config: dict, parameter_keys: str | list[Union[str, list[str], list[Union[str, int]]]] = None
) -> dict:
    config["optimization_options"] = config.get("optimization_options", {})
    for key in ["experiment", "generation_strategy", "scheduler"]:
        config["optimization_options"][key] = config["optimization_options"].get(key, {})
    config["optimization_options"]["experiment"]["name"] = config["optimization_options"]["experiment"].get("name", "")

    if parameter_keys:
        parameters, mapping = wpr_params_to_boa(config, parameter_keys)
        config["parameters"] = parameters
        config["optimization_options"]["mapping"] = mapping

    # Format parameters for Ax experiment
    config["parameters_orig"] = deepcopy(config.get("parameters", {}))
    config["parameter_constraints_orig"] = deepcopy(config.get("parameter_constraints", []))

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


def wpr_params_to_boa(params: dict, parameter_keys: str | list[Union[str, list[str], list[Union[str, int]]]]) -> dict:
    """

    Parameters
    ----------
    params : dict
        dictionary containing parameters
    parameter_keys :  str | list[Union[str, list[str], list[Union[str, int]]]]
        str of key to parameters, or list of json paths to key(s) of parameters.


    Returns
    -------

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
            # mapping[new_key] = dict(path=maybe_key, original_key=parameter_name)
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


def get_dt_now_as_str(fmt: str = "%Y%m%dT%H%M%S"):
    return dt.datetime.now().strftime(fmt)


def make_experiment_dir(working_dir: str, experiment_name: str = ""):
    """
    Creates directory for the experiment and returns the path.
    The directory is named with the experiment name and the current datetime.

    Parameters
    ----------
    working_dir : str
        Working directory, the parent directory where the experiment directory will be written
    experiment_name: str
        Name of the experiment

    Returns
    -------
    Path
        Path to the directory for the experiment
    """
    # Directory named with experiment name and datetime
    experiment_name = experiment_name + "_" if experiment_name else experiment_name
    ex_dir = Path(working_dir) / f"{experiment_name}{get_dt_now_as_str()}"
    ex_dir.mkdir()
    return ex_dir


def zfilled_trial_index(trial_index: int, fill_size: int = 6) -> str:
    """Return trial index left passed with zeros of length ``fill_size``"""
    return str(trial_index).zfill(fill_size)


def get_trial_dir(experiment_dir: os.PathLike, trial_index: int, **kwargs):
    """
    Return a directory for a trial,
    Trial directory is named with the trial index.

    Parameters
    ----------
    experiment_dir : os.PathLike
        Directory for the experiment
    trial_index : int
        Trial index from the Ax client
    kwargs
        kwargs passed to ``zfilled_trial_index``

    Returns
    -------
    Path
        Directory for the trial
    """
    trial_dir = Path(experiment_dir) / zfilled_trial_index(trial_index, **kwargs)  # zero-padded trial index
    return trial_dir


def make_trial_dir(experiment_dir: os.PathLike, trial_index: int, **kwargs):
    """
    Create a directory for a trial, and return the path to the directory.
    Trial directory is created inside the experiment directory, and named with the trial index.
    Model configs and outputs for each trial will be written here.

    Parameters
    ----------
    experiment_dir : os.PathLike
        Directory for the experiment
    trial_index : int
        Trial index from the Ax client
    kwargs
        kwargs passed to ``get_trial_dir``

    Returns
    -------
    Path
        Directory for the trial
    """
    trial_dir = get_trial_dir(experiment_dir, trial_index, **kwargs)
    trial_dir.mkdir()
    return trial_dir


def write_configs(trial_dir, parameters, model_options):
    """
    Write model configuration file for each trial (model run). This is the config file used by FETCH3
    for the model run.

    The config file is written as ```config.yml``` inside the trial directory.

    Parameters
    ----------
    trial_dir : Path
        Trial directory where the config file will be written
    parameters : list
        Model parameters for the trial, generated by the ax client
    model_options : dict
        Model options loaded from the experiment config yml file.

    Returns
    -------
    str
        Path for the config file.
    """
    with open(trial_dir / "config.yml", "w") as f:
        # Write model options from loaded config
        # Parameters for the trial from Ax
        config_dict = {"model_options": model_options, "parameters": parameters}
        yaml.dump(config_dict, f)
        return f.name


config = {
    "params": {
        "a": {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}},
        "b": {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}},
    },
    "params2": [
        {0: {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}}},
        {0: {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}}},
    ],
    "params_a": {"x1": {"bounds": [0, 1], "type": "range"}, "x2": {"type": "fixed", "value": 0.5}},
}
