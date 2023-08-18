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
from functools import wraps
from typing import TYPE_CHECKING, Type

import ruamel.yaml as yaml
from ax.core.base_trial import BaseTrial
from ax.core.parameter import ChoiceParameter, FixedParameter, RangeParameter
from ax.exceptions.core import AxError
from ax.storage.json_store.encoder import object_to_json
from ax.utils.common.docutils import copy_doc

from boa.definitions import IS_WINDOWS, PathLike, PathLike_tup
from boa.logger import get_logger
from boa.template import render_template_from_path
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
    >>> with cd_and_cd_back():
    ...     # with do some things that change the directory
    ...     os.chdir("..")
    ... # When we exit the context manager (dedent) we go back to the starting directory
    >>> ending_dir = os.getcwd()
    >>> assert starting_dir == ending_dir

    >>> starting_dir = os.getcwd()
    >>> path_to_change_to = ".."
    >>> with cd_and_cd_back(path=path_to_change_to):
    ...     # with do some things inside the context manager
    ...     pass
    ... # When we exit the context manager (dedent) we go back to the starting directory
    >>> ending_dir = os.getcwd()
    >>> assert starting_dir == ending_dir

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
    >>> @cd_and_cd_back_dec()
    ... def foo():
    ...     os.chdir("..")

    >>> starting_dir = os.getcwd()
    >>> foo()
    >>> ending_dir = os.getcwd()
    >>> assert starting_dir == ending_dir

    >>> @cd_and_cd_back_dec(path="..")
    ... def bar():
    ...     os.chdir("..")

    >>> starting_dir = os.getcwd()
    >>> bar()
    >>> ending_dir = os.getcwd()
    >>> assert starting_dir == ending_dir

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
        try:
            module = _load_module_from_path(wrapper)
            WrapperCls: Type[BaseWrapper] = _load_attr_from_module(module, wrapper_name)
        except Exception:
            from boa.wrappers.script_wrapper import ScriptWrapper

            WrapperCls = ScriptWrapper
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


def load_json(file: PathLike, **kwargs) -> dict:
    """
    Read experiment configuration file for setting up the optimization.
    The configuration file contains the list of parameters, and whether each parameter is a fixed
    parameter or a range parameter. Fixed parameters have a value specified, and range
    parameters have a range specified.

    Parameters
    ----------
    file
        File path for the experiment configuration file
    kwargs
        variables to pass to :func:`boa.template.render_template_from_path`
        for rendering in your loaded file

    Examples
    --------

        config_path = Path("path/to/your/config.json_or_yaml")
        config = load_jsonlike(config_path)

    Returns
    -------
    loaded_configs: dict

    """
    file = pathlib.Path(file).expanduser()
    s = render_template_from_path(file, **kwargs)
    config = json.loads(s)
    return config


@copy_doc(load_json)
def load_yaml(file: PathLike, **kwargs) -> dict:
    file = pathlib.Path(file).expanduser()
    s = render_template_from_path(file, **kwargs)
    config: dict = yaml.safe_load(s)
    return config


@copy_doc(load_json)
def load_jsonlike(file: PathLike, **kwargs) -> dict:
    file = pathlib.Path(file)
    if file.suffix.lstrip(".").lower() in {"yaml", "yml"}:
        return load_yaml(file, **kwargs)
    elif file.suffix.lstrip(".").lower() == "json":
        return load_json(file, **kwargs)
    else:
        raise ValueError(f"Invalid config file format for config file {file}\nAccepted file formats are YAML and JSON.")


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
