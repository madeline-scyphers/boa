"""
########################
Base Wrapper
########################

"""

from __future__ import annotations

import pathlib

from ax.core.base_trial import BaseTrial
from ax.storage.json_store.encoder import object_to_json

from boa.definitions import PathLike
from boa.logger import get_logger
from boa.metaclasses import WrapperRegister
from boa.wrappers.wrapper_utils import (
    initialize_wrapper,
    load_jsonlike,
    make_experiment_dir,
    normalize_config,
)

logger = get_logger()


class BaseWrapper(metaclass=WrapperRegister):
    _path: PathLike
    """

    Parameters
    ----------
    config_path
    args
    kwargs
    """

    def __init__(self, config_path: PathLike = None, config: dict = None, setup=True, *args, **kwargs):
        self.config_path = config_path
        self._experiment_dir = None
        self._working_dir = None
        self._output_dir = None
        self.ex_settings = {}
        self.model_settings = {}
        self.script_options = {}
        self._metric_cache = {}
        self._metric_properties = {}
        self._metric_names = kwargs.get("metric_names", [])

        self.config = None
        if config:
            self.config = config

        elif config_path:
            config = self.load_config(config_path, *args, **kwargs)
            # if load_config returns something, set to self.config
            # if users overwrite load_config and don't return anything,
            # we assume they set self.config in load_config and don't want
            # to override it here (and set it to None)
            if config is not None:
                self.config = config

        if setup and self.config:
            experiment_dir = self.mk_experiment_dir(*args, **kwargs)
            if not self.experiment_dir:
                if experiment_dir:
                    self.experiment_dir = experiment_dir
                elif self.ex_settings["experiment_dir"]:
                    self.experiment_dir = self.ex_settings["experiment_dir"]
                else:
                    raise ValueError("No experiment_dir set or returned from mk_experiment_dir")

    @property
    def metric_names(self):
        """list of metric names associated with this experiment"""
        # in case users subclass without super
        if not hasattr(self, "_metric_names"):
            self._metric_names = []
        return self._metric_names

    @metric_names.setter
    def metric_names(self, metric_names):
        if metric_names:
            self._metric_names = metric_names
        else:
            self._metric_names = []

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, config):
        self._config = config or {}
        if self._config:
            self.ex_settings = self._config["optimization_options"]
            self.model_settings = self._config.get("model_options", {}) or {}
            self.script_options = self._config.get("script_options", {}) or {}
            metric_propertis = {}
            for metric in self.ex_settings["objective_options"]["objectives"]:
                if "properties" in metric:
                    name = (
                        metric.get("name")
                        or metric.get("metric")
                        or metric.get("boa_metric")
                        or metric.get("synthetic_metric")
                        or metric.get("sklearn_metric")
                    )
                    metric_propertis[name] = metric["properties"]

            self._metric_properties = metric_propertis

    @property
    def experiment_dir(self):
        return self._experiment_dir

    @experiment_dir.setter
    def experiment_dir(self, experiment_dir: PathLike):
        if experiment_dir:
            self._experiment_dir = pathlib.Path(experiment_dir).resolve()
        else:
            self._experiment_dir = experiment_dir

    @property
    def working_dir(self):
        return self._working_dir

    @working_dir.setter
    def working_dir(self, working_dir: PathLike):
        if working_dir:
            self._working_dir = pathlib.Path(working_dir).resolve()
        else:
            self._working_dir = working_dir

    @property
    def output_dir(self):
        return self._output_dir

    @output_dir.setter
    def output_dir(self, output_dir: PathLike):
        if output_dir:
            self._output_dir = pathlib.Path(output_dir).resolve()
        else:
            self._output_dir = output_dir

    @classmethod
    def path(cls):
        """Path of file that the Wrapper class is defined in"""
        return cls._path

    def load_config(self, config_path: PathLike, *args, **kwargs) -> dict:
        """
        Load config takes a configuration path of either a JSON file or a YAML file and returns
        your configuration dictionary.

        Load_config will (unless overwritten in a subclass), do some basic "normalizations"
        to your configuration for convenience. See :func:`.normalize_config`
        for more information about how the normalization works and what config options you
        can control.

        This implementation offers a default implementation that should work for most JSON or YAML
        files, but can be overwritten in subclasses if need be.

        Parameters
        ----------
        config_path
            File path for the experiment configuration file

        Returns
        -------
        dict
            loaded_config
        """
        try:
            config = load_jsonlike(config_path, normalize=False)
        except ValueError as e:  # return empty config if not json or yaml file
            logger.warning(repr(e))
            return {}
        parameter_keys = config.get("optimization_options", {}).get("parameter_keys", None)
        config = normalize_config(config=config, parameter_keys=parameter_keys)

        self.config = config
        return self.config

    def mk_experiment_dir(
        self,
        experiment_dir: PathLike = None,
        output_dir: PathLike = None,
        experiment_name: str = None,
        append_timestamp: bool = None,
        **kwargs,
    ) -> pathlib.Path:
        """
        Make the experiment directory that boa will write all of its trials and logs to.

        All parameters can be set in your configuration file as well.
        experiment_dir -> optimization_options -> experiment_dir
        experiment_name -> optimization_options -> experiment -> name
        append_timestamp -> script_options -> append_timestamp

        Parameters
        ----------
        experiment_dir
            Path to the directory for the output of the experiment
            You may specify this or output_dir in your configuration file instead.
            (Defaults to your configuration file and then None)
        output_dir: PathLike
            Output directory of project, experiment_dir will be placed inside
            output dir based on experiment name.
            Because of this only either experiment_dir or output_dir may be specified.
            You may specify this or experiment_dir in your configuration file instead.
            (Defaults to your configuration file and then None, if neither
            experiment_dir nor output_dir are specified, output_dir defaults
            to whatever pwd returns (and equivalent on windows))
        experiment_name: str
            Name of experiment, used for creating path to experiment dir with the output dir
            (Defaults to your configuration file and then boa_runs)
        append_timestamp : bool
            Whether to append a timestamp to the end of the experiment directory
            to ensure uniqueness
            (Defaults to your configuration file and then True)
        """
        # grab exp dir from config file or if passed in
        experiment_dir = experiment_dir or self.ex_settings.get("experiment_dir")
        output_dir = output_dir or self.ex_settings.get("output_dir")
        experiment_name = experiment_name or self.ex_settings.get("experiment", {}).get("name", "boa_runs")
        append_timestamp = (
            append_timestamp
            or self.ex_settings.get("append_timestamp")
            or self.script_options.get("append_timestamp", True)
        )
        if experiment_dir:
            mk_exp_dir_kw = dict(experiment_dir=experiment_dir, append_timestamp=append_timestamp, **kwargs)
        else:  # if no exp dir, instead grab output dir from config or passed in
            if not output_dir:
                # if no output dir (or exp dir) set to cwd
                output_dir = pathlib.Path.cwd()

            mk_exp_dir_kw = dict(
                output_dir=output_dir, experiment_name=experiment_name, append_timestamp=append_timestamp, **kwargs
            )

            # We use str() because make_experiment_dir returns a Path object (json serialization)
            self.ex_settings["output_dir"] = str(output_dir)
            self.output_dir = output_dir

        experiment_dir = make_experiment_dir(**mk_exp_dir_kw)

        self.ex_settings["experiment_dir"] = str(experiment_dir)
        self.experiment_dir = experiment_dir
        return experiment_dir

    def setup(self, *args, **kwargs):
        """
        method to override for subclasses to run any setup code they need either on class init
        (which will happen by default unless passing setup=False) or after init by
        calling this method directly

        By default, this method will run mk_experiment_directory, so if you override this
        method to do more setup, either include that a call to mk_experiment_directory,
        (the default version or your own implementation) or call ``super().setup(*args, **kwargs)``
        which will then call the original version, which will call mk_experiment_directory.
        """
        return self.mk_experiment_directory(*args, **kwargs)

    def write_configs(self, trial: BaseTrial) -> None:
        """
        This function is usually used to write out the configurations files used
        in an individual optimization trial run, or to dynamically write a run
        script to start an optimization trial run.

        Parameters
        ----------
        trial
        """

    def run_model(self, trial: BaseTrial) -> None:
        """
        Runs a model by deploying a given trial.

        Parameters
        ----------
        trial
        """
        raise NotImplementedError(
            "Please subclass BaseWrapper to to use the run_model features."
            "\nOr if deserializing, check that your wrapper deserialized properly,"
            "\nff it did not you may need to directly pass in the pass to "
            "`scheduler_from_json_file`."
            "\nOr an instantiated wrapper."
        )

    def set_trial_status(self, trial: BaseTrial) -> None:
        """
        Marks the status of a trial to reflect the status of the model run for the trial.

        Each trial will be polled periodically to determine its status (completed, failed, still running,
        etc). This function defines the criteria for determining the status of the model run for a trial (e.g., whether
        the model run is completed/still running, failed, etc). The trial status is updated accordingly when the trial
        is polled.

        The approach for determining the trial status will depend on the structure of the particular model and its
        outputs. One example is checking the log files of the model.

        .. todo::
            Add examples/links of different approaches

        Parameters
        ----------
        trial

        Examples
        --------
        trial.mark_completed()
        trial.mark_failed()
        trial.mark_abandoned()
        trial.mark_early_stopped()

        You can also do:

            from ax.core.base_trial import TrialStatus
            trial.mark_as(TrialStatus.COMPLETED)

        or:

            trial.mark_as(3)  # TrialStatus is an ENUM with COMPLETED being equivalent to 3

        **Relevant ENUM list**

        You can set it to either to text version, or the numerical equivalent

        ==================  =====
        Relevant ENUM list   Numerical Equivalent
        ==================  =====
        FAILED                2
        COMPLETED             3
        RUNNING               4 -- you don't need to set it to running, it is already set to running
        ABANDONED             4
        EARLY_STOPPED         7
        ==================  =====

        See Also
        --------
        # TODO add sphinx link to ax trial status
        """

    def _fetch_trial_data(self, trial: BaseTrial, metric_name: str, *args, **kwargs):
        # in case users don't subclass with super
        if not hasattr(self, "_metric_cache"):
            self._metric_cache = {}
        if trial.index not in self._metric_cache:
            self._metric_cache[trial.index] = {}
        if metric_name in self._metric_cache[trial.index]:
            return self._metric_cache[trial.index][metric_name]
        res = self.fetch_trial_data(
            trial=trial, metric_properties=self._metric_properties, metric_name=metric_name, *args, **kwargs
        )
        if res is None:
            raise ValueError(
                "No data returned when fetching Metric!"
                " Make sure you return something form `fetch_trial_data`"
                " or if using language agnostic setup, write out your data as specified in"
                " the Wrapper docs."
            )
        if not isinstance(res, dict):
            res = {"wrapper_args": res}
        if metric_name not in res:
            res = {metric_name: res}
        self._metric_cache[trial.index].update(res)

        for name in self._metric_cache[trial.index].keys():
            if self.metric_names and name not in self.metric_names:
                logger.warning(f"found extra returned metric: {name} in returned metrics from fetch_trial_data")
        return self._metric_cache[trial.index][metric_name]

    def fetch_trial_data(self, trial: BaseTrial, metric_properties: dict, metric_name: str, *args, **kwargs) -> dict:
        """
        Retrieves the trial data for either the one metric that is specified in metric_name or all
        metrics at once.

        For example, for a case where you are minimizing the error between a model and observations, using RMSE as a
        metric, this function would load the model output and the corresponding observation data that will be passed to
        the RMSE metric.

        The return value of this function is a dictionary of dictionaries.
        The keys are the names of the metrics that each dictionary goes to, then each
        sub dictionary is the key value pair of parameters to pass to those metric functions.
        If you are just returning one metric, you do not need to return an embedded dictionary,
        and can just return the dictionary of key value parameter pairs.

        In the key value parameter pairs, you can also specify the key "sem" for the standard error
        for this metric on this trial.

        Parameters
        ----------
        trial
            The current trial. parameters can be accessed as trial.arm.parameters and trial
            index can be accessed by trial.index
        metric_properties
            collection of all metric properties for all metrics as a nested dictionary.
            a specific metric properties can be accessed as `metric_properties["metric_name1"]`
        metric_name
            the name of the metric that the arguments are being fetched for if you
            choose to only return one metric at a time

        Returns
        -------
        dict
            A dictionary with the keys being the name of a specific metric, and the values
            being a dictionary of key word arguments to pass to that metric function.
            ex: Mean uses' np.mean, which expects the parameters a (a array like object),
            so you could return {"Mean": {"a": [1, 2, 3, 4]}}
            You can also include a key "sem" that is the standard error of the mean for
            these trials metric value.

            example return values

            .. code-block:: python

                {
                    "Mean": {"a": trial.arm.parameters, "sem": 4.5},
                    "RMSE": {
                        "y_true": [1.12, 1.25, 2.54, 4.52],
                        "y_pred": trial.arm.parameters,
                    },
                }

            .. code-block:: python

                {"Mean": {"a": trial.arm.parameters}}

            .. code-block:: python

                {"a": trial.arm.parameters, "sem": 1}

        Examples
        --------
        This example returns all the metrics at once.
        You can imagine instead having a "calc_stuff" for whatever you need to throw into these

        >>> def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        ...     return {
        ...         "Mean": {"a": trial.arm.parameters.values(), "sem": 4.5},
        ...         "RMSE": {
        ...             "y_true": [1.12, 1.25, 2.54, 4.52],
        ...             "y_pred": trial.arm.parameters.values(),
        ...         },
        ...     }

        This one only returns one metric at a time, it has some fragilities in that if you change
        the name of the metrics in the config, this will break. But for quick and dirty things, this
        can be great.

        >>> def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        ...     if metric_name == "Mean":
        ...         return {"a": trial.arm.parameters.values(), "sem": 4.5}
        ...     elif metric_name == "RMSE":
        ...         return {
        ...             "y_true": [1.12, 1.25, 2.54, 4.52],
        ...             "y_pred": trial.arm.parameters.values(),
        ...         }

        This one is a little more complicated, but it assumes in your config for each metric, you
        define a properties section, which allows arbitrary information to be passed. You can then
        associate a particular metric with a function and lookup that function at runtime in a dictionary
        (a hashmap if coming from other languages).

        >>> def func_a(array):
        ...     return np.mean(np.exp(array))
        ...
        ... def func_b(array):
        ...     return np.exp(np.mean(array))
        ...
        ... funcs = {func_a.__name__: func_a, func_b.__name__: func_b}
        ...
        ... def fetch_trial_data(self, trial, metric_properties, metric_name, *args, **kwargs):
        ...     # we define in our config the names of functions to associate with certain metrics
        ...     # and look them up at run time
        ...     return {"a": funcs[metric_properties[metric_name]["function"]](trial.arm.parameters)}
        """

    def to_dict(self) -> dict:
        """Convert BaseWrapper to a dictionary."""

        properties = object_to_json(
            dict(
                path=str(self._path),
                experiment_dir=self.experiment_dir,
                working_dir=self.working_dir,
                output_dir=self.output_dir,
                metric_names=self.metric_names,
                config=self.config,
                config_path=self.config_path,
                name=self.__class__.__name__,
                __type=self.__class__.__name__,
            )
        )
        return properties

    @classmethod
    def from_dict(cls, **kwargs):
        return initialize_wrapper(
            wrapper=cls,
            post_init_attrs=dict(
                experiment_dir=kwargs.get("experiment_dir"),
                working_dir=kwargs.get("working_dir"),
                output_dir=kwargs.get("output_dir"),
                metric_names=kwargs.get("metric_names"),
                config=kwargs.get("config", {}),
            ),
            setup=False,
            **kwargs,
        )
