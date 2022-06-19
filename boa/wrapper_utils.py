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

import datetime as dt
import logging
import os
from contextlib import contextmanager
from copy import deepcopy
from functools import wraps
from pathlib import Path
from pprint import pformat

import yaml
from ax.core.parameter import ChoiceParameter, FixedParameter, RangeParameter
from ax.service.utils.instantiation import EXPECTED_KEYS_IN_PARAM_REPR
from ax.service.utils.instantiation import PARAM_CLASSES as PARAM_CLASSES_AX

from boa.utils import get_callable_signature, get_dictionary_from_callable

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


def load_experiment_config(config_file: os.PathLike) -> dict:
    """
    Read experiment configuration yml file for setting up the optimization.
    yml file contains the list of parameters, and whether each parameter is a fixed
    parameter or a range parameter. Fixed parameters have a value specified, and range
    parameters have a range specified.

    Parameters
    ----------
    config_file : os.PathLike
        File path for the experiment configuration file

    Returns
    -------
    loaded_configs: dict
    """

    # Load the experiment config yml file
    with open(config_file, "r") as yml_config:
        config = yaml.safe_load(yml_config)

    return normalize_config(config)


def normalize_config(config: os.PathLike) -> dict:
    # Format parameters for Ax experiment
    search_space_parameters = []
    assert PARAM_CLASSES_AX == list(
        PARAM_CLASSES.keys()
    ), "PARAM_CLASSES has changed, normalize_config util function may be out of date."
    for param in config.get("parameters", {}).keys():
        param_dict = config["parameters"][param]
        parameter_type = param_dict["type"]
        parameter_cls = PARAM_CLASSES[parameter_type]
        for p in param_dict:
            if p not in EXPECTED_KEYS_IN_PARAM_REPR:
                logger.warning(
                    "Parameter %s includes unexpected parameter %s. "
                    "\nIt is fine to use other arguments here for your model "
                    "and not the optimization"
                    "\nbut check that this isn't a typo or mistake.",
                    param,
                    p,
                )

        d = get_dictionary_from_callable(parameter_cls.__init__, deepcopy(param_dict))
        removed_params = set(param_dict) - set(d)
        logger.info("Removed parameters from param %s:\n%s", param, pformat(removed_params))

        d["name"] = param  # Add "name" attribute for each parameter

        search_space_parameters.append(d)

    # Parameters from dictionary to list
    config["parameters_orig"] = deepcopy(config.get("parameters", {}))
    config["parameter_constraints_orig"] = config.get("parameter_constraints", [])

    config["parameters"] = search_space_parameters

    config["optimization_options"] = config.get("optimization_options", {})
    for key in ["metric", "experiment", "generation_strategy", "scheduler"]:
        config["optimization_options"][key] = config["optimization_options"].get(key, {})

    return config


def make_experiment_dir(working_dir: str, experiment_name: str):
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
    ex_dir = Path(working_dir) / f'{experiment_name}_{dt.datetime.now().strftime("%Y%m%dT%H%M%S")}'
    ex_dir.mkdir()
    return ex_dir


def get_trial_dir(experiment_dir, trial_index):
    """
    Return a directory for a trial,
    Trial directory is named with the trial index.

    Parameters
    ----------
    experiment_dir : Path
        Directory for the experiment
    trial_index : int
        Trial index from the Ax client

    Returns
    -------
    Path
        Directory for the trial
    """
    trial_dir = experiment_dir / str(trial_index).zfill(6)  # zero-padded trial index
    return trial_dir


def make_trial_dir(experiment_dir, trial_index):
    """
    Create a directory for a trial, and return the path to the directory.
    Trial directory is created inside the experiment directory, and named with the trial index.
    Model configs and outputs for each trial will be written here.

    Parameters
    ----------
    experiment_dir : Path
        Directory for the experiment
    trial_index : int
        Trial index from the Ax client

    Returns
    -------
    Path
        Directory for the trial
    """
    trial_dir = get_trial_dir(experiment_dir, trial_index)
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
        Path for the config file
    """
    with open(trial_dir / "config.yml", "w") as f:
        # Write model options from loaded config
        # Parameters for the trial from Ax
        config_dict = {"model_options": model_options, "parameters": parameters}
        yaml.dump(config_dict, f)
        return f.name