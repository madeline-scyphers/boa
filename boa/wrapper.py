from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

from ax.core.base_trial import BaseTrial, TrialStatus
from ax.exceptions.core import AxError
from ax.storage.json_store.encoder import object_to_json

import boa.metrics.metrics
from boa.metaclasses import WrapperRegister
from boa.utils import get_dictionary_from_callable
from boa.wrapper_utils import (
    get_trial_dir,
    load_jsonlike,
    make_experiment_dir,
    normalize_config,
    split_shell_command,
)

logger = logging.getLogger(__name__)


class BaseWrapper(metaclass=WrapperRegister):
    def __init__(self, config_path: os.PathLike = None, *args, **kwargs):
        self.model_settings = None
        self.ex_settings = None
        self.experiment_dir = None

        if config_path:
            self.config = None
            config = self.load_config(config_path, *args, **kwargs)
            # if load_config returns something, set to self.config
            # if users overwrite load_config and don't return anything, we don't
            # want to set it to self.config if they set it in load_config
            if config is not None:
                self.config = config
            self.mk_experiment_dir(*args, **kwargs)

    def load_config(self, config_path: os.PathLike, *args, **kwargs):
        """
        Load config file and return a dictionary # TODO finish this

        Parameters
        ----------
        config_path : os.PathLike
            File path for the experiment configuration file

        Returns
        -------
        loaded_config: dict
        """
        try:
            config = load_jsonlike(config_path, normalize=False)
        except ValueError as e:  # return empty config if not json or yaml file
            logger.warning(repr(e))
            return {}
        parameter_keys = config.get("optimization_options", {}).get("parameter_keys", None)
        config = normalize_config(config=config, parameter_keys=parameter_keys)

        self.config = config
        self.ex_settings = self.config["optimization_options"]
        self.model_settings = self.config.get("model_options", {})
        return self.config

    def mk_experiment_dir(
        self,
        experiment_dir: os.PathLike = None,
        working_dir: os.PathLike = None,
        experiment_name: str = None,
        append_timestamp: bool = True,
        **kwargs,
    ):
        """
        Make the experiment directory that boa will write all of its trials and logs to.

        Parameters
        ----------
        experiment_dir: os.PathLike
            Path to the directory for the output of the experiment
            You may specify this or working_dir in your configuration file instead.
            (Defaults to None and using your configuration file instead)
        working_dir: os.PathLike
            Working directory of project, experiment_dir will be placed inside
            working dir based on experiment name.
            Because of this only either experiment_dir or working_dir may be specified.
            You may specify this or experiment_dir in your configuration file instead.
            (Defaults to None and using your configuration file instead)
        experiment_name: str
            Name of experiment, used for creating path to experiment dir with the working dir
            (Defaults to None and using your configuration file instead)
        append_timestamp : bool
            Whether to append a timestamp to the end of the experiment directory
            to ensure uniqueness
        """
        # grab exp dir from config file or if passed in
        experiment_dir = experiment_dir or self.ex_settings.get("experiment_dir")
        working_dir = working_dir or self.ex_settings.get("working_dir")
        experiment_name = experiment_name or self.ex_settings.get("experiment", {}).get("name", "boa_runs")
        if experiment_dir:
            mk_exp_dir_kw = dict(experiment_dir=experiment_dir, append_timestamp=append_timestamp)
        else:  # if no exp dir, instead grab working dir from config or passed in
            if not working_dir:
                # if no working dir (or exp dir) set to cwd
                working_dir = Path.cwd()

            mk_exp_dir_kw = dict(
                working_dir=working_dir, experiment_name=experiment_name, append_timestamp=append_timestamp
            )

            # We use str() because make_experiment_dir returns a Path object (json serialization)
            self.ex_settings["working_dir"] = str(working_dir)

        experiment_dir = make_experiment_dir(**mk_exp_dir_kw)
        self.ex_settings["experiment_dir"] = str(experiment_dir)
        self.experiment_dir = experiment_dir

    def write_configs(self, trial: BaseTrial) -> None:
        """
        This function is usually used to write out the configurations files used
        in an individual optimization trial run, or to dynamically write a run
        script to start an optimization trial run.

        Parameters
        ----------
        trial : BaseTrial
        """
        # write_configs_path = self.config.get("script_options", {}).get("write_configs_path")
        self._run_subprocess_script_cmd(trial, "write_configs")

    def run_model(self, trial: BaseTrial) -> None:
        """
        Runs a model by deploying a given trial.

        Parameters
        ----------
        trial : BaseTrial
        """
        self._run_subprocess_script_cmd(trial, "run_model", block=False)

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
        trial : BaseTrial

        Examples
        --------
        trial.mark_completed()
        trial.mark_failed()
        trial.mark_abandoned()
        trial.mark_early_stopped()

        # You can also do
        from ax.core.base_trial import TrialStatus
        trial.mark_as(TrialStatus.COMPLETED)
        # or
        trial.mark_as(3)  # TrialStatus is an ENUM with COMPLETED being equivalent to 3

        Relevant ENUM list
        ------------------
        # FAILED = 2
        # COMPLETED = 3
        # RUNNING = 4  # you don't need to set it to running, it is already set to running
        # ABANDONED = 5
        # EARLY_STOPPED = 7

        See Also
        --------
        # TODO add sphinx link to ax trial status
        """

        script_was_ran = self._run_subprocess_script_cmd(trial, "set_trial_status")
        if script_was_ran:
            data = self._read_subprocess_script_output(trial, "set_trial_status")
            trial_status_keys = [k for k in data.keys() if k.lower() == "trialstatus"]
            if trial_status_keys:
                trial_status_key = trial_status_keys[0]
                trial_status = data[trial_status_key]
                # some languages jsonify dicts as 1 element lists sometimes
                if isinstance(trial_status, list):
                    trial_status = trial_status[0]
                try:
                    # convert trial_status to an enum for trial.mark_as
                    try:  # if it is an int or a str of an int this will work
                        trial_status = TrialStatus(int(trial_status))
                    # if it is a string of a trial status name ("completed" etc.), then get the TrialStatus enum version
                    except ValueError:
                        trial_status = TrialStatus[trial_status.upper()]
                    # you can't set a running trial to running, so we leave, which is equivalent
                    if trial_status != TrialStatus.RUNNING:
                        trial.mark_as(trial_status)
                except ValueError as e:
                    raise ValueError(f"Invalid trial status - {trial_status} - passed to `set_trial_status`") from e

    def fetch_trial_data(self, trial: BaseTrial, metric_properties: dict, metric_name: str, *args, **kwargs) -> dict:
        """
        Retrieves the trial data and prepares it for the metric(s) used in the objective
        function.

        For example, for a case where you are minimizing the error between a model and observations, using RMSE as a
        metric, this function would load the model output and the corresponding observation data that will be passed to
        the RMSE metric.

        The return value of this function is a dictionary, with keys that match the keys
        of the metric used in the objective function.
        # TODO work on this description

        Parameters
        ----------
        trial : BaseTrial
        metric_properties: dict
        metric_name: str

        Returns
        -------
        dict
            A dictionary with the keys matching the keys of the metric function
                used in the objective
        """

        script_was_ran = self._run_subprocess_script_cmd(trial, "fetch_trial_data")
        if script_was_ran:
            data = self._read_subprocess_script_output(trial, "fetch_trial_data")

            for key, values in data.items():
                if key.lower() == metric_name.lower():
                    metric_closure = boa.metrics.metrics._get_boa_metric_any_case(metric_name)
                    metric = metric_closure()
                    return get_dictionary_from_callable(metric.metric_to_eval.func, values)

    def _run_subprocess_script_cmd(self, trial: BaseTrial, func_name: str, block: bool = True, **kwargs):
        """
        Run a script command from their config file in a subproccess.
        Dump the trial data into a json file for them to collect if need be
        and pass to the script command as a command line argument.

        Parameters
        ----------
        trial : BaseTrial
            Current trial that will be dumped to json
        func_name : str
            Name of function that is calling this func.
            Used as a predictable basis to name outgoing data files
        block : bool
            Whether to block until subprocess completes (defaults to False)

        Returns
        -------
        bool
            True if a script was run, False otherwise
        """
        run_cmd = self.config.get("script_options", {}).get(f"{func_name}_run_cmd")
        if run_cmd:
            # TODO BaseTrial doesn't have arm property, just arms.
            # With issue #22, fix this to fully support Batched Trials
            trial_dir = get_trial_dir(self.experiment_dir, trial.index)
            trial_dir.mkdir(parents=True, exist_ok=True)
            kw = {}
            for key, value in kwargs.items():
                try:
                    kw[key] = object_to_json(value)
                except (AxError, ValueError) as e:
                    kw[key] = str(value)
                    logger.warning(e)
            data = {
                "parameters": object_to_json(trial.arm.parameters),
                "trial": object_to_json(trial),
                "trial_index": trial.index,
                "trial_dir": str(trial_dir),
                **kw,
            }
            output_file = trial_dir / f"{func_name}_to_wrapper.json"
            with open(output_file, "w+") as file:  # pragma: no cover
                file.write(json.dumps(data))

            args = split_shell_command(f"{run_cmd} {output_file}")
            p = subprocess.Popen(args, stdout=subprocess.PIPE, universal_newlines=True)
            if block:
                p.communicate()
            # TODO move polling and print to another thread so it doesn't block but still writes to log?
            # Grab stdout line by line as it becomes available.
            # This will loop until p terminates.
            # while p.poll() is None:
            #     l = p.stdout.readline()  # This blocks until it receives a newline.
            #     if l:
            #         logger.info(l)
            # # When the subprocess terminates there might be unconsumed output
            # # that still needs to be processed.
            # l = p.stdout.read()
            # if l:
            #     logger.info(l)
            return True
        return False

    def _read_subprocess_script_output(self, trial: BaseTrial, func_name: str):
        run_cmd = self.config.get("script_options", {}).get(f"{func_name}_run_cmd")
        if run_cmd:
            trial_dir = get_trial_dir(self.experiment_dir, trial.index)
            output_files = trial_dir.glob(f"{func_name}_from_wrapper.*")
            json_output_files = [file for file in output_files if file.suffix.lower() in {".json", ".yml", ".yaml"}]
            if len(json_output_files) > 1:
                raise ValueError(f"{func_name} can only output one json or yaml output file")
            elif len(json_output_files) == 1:
                output_file = json_output_files[0]
                if output_file.exists():
                    return load_jsonlike(output_file, normalize=False)
            return {}
