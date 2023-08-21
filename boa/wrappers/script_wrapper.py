from __future__ import annotations

import subprocess
from typing import Iterable

from ax import Trial
from ax.core.base_trial import TrialStatus

from boa.logger import get_logger
from boa.wrappers.base_wrapper import BaseWrapper
from boa.wrappers.wrapper_utils import (
    get_trial_dir,
    load_jsonlike,
    save_trial_data,
    split_shell_command,
)

logger = get_logger()


OUTPUT_FILES = ("output", "outputs", "result", "results", "metric", "metrics")


class ScriptWrapper(BaseWrapper):
    """This is the Wrapper that will control calling your scripts you specify in your configuration
    file.

    On every script it calls, it will add an addition command line argument at the end that
    is the path to the trial directory for the trial that is being run (you can't rely on the
    newest directory created since the trials are run in parallel). It will place a number of data
    json files in this directory for you to access that should include any and all information you
    need to run your scripts. ``parameters.json`` includes all of the parameters for that trial.
    ``trial.json`` includes the complete json serialization of the current trial (including the
    parameters, this is usually more than you need, but has lots of information, such as the trial index
    (You also know that by the trial dir path you are passed), ``data.json`` which includes
    which is a comprehensive json file of everything above, as well as the param_names from your
    config file for each metric, and the metric_properties you custom configure for any individual
    metric (though metric_properties is only available in the final stages when fetch_trial_status
    is being called).
    """

    def write_configs(self, trial: Trial) -> None:
        """
        It can be convenient to separate our your writing out model configuration files
        from your run_model script. If this is the case, then if you include a script option
        in your configuration file to run this command, you can output whatever configuration
        files your model might need. Maybe your model needs certain configuration files
        in certain places, or your parameters create some files like NetCDF. Whatever it is,
        if you want to separate out your logic for creating the configuration for your model
        and running your model, write a script to do it, and put in your script_options
        section the command to run said command before the run_model command.

        BOA will write out some data files for you to process the data.

        Parameters
        ----------
        trial : Trial
        """
        param_names = {metric.name: metric.param_names for metric in self.config.objective.metrics}
        kw = {"param_names": param_names} if param_names else {}
        self._run_subprocess_script_cmd_if_exists(trial, "write_configs", **kw)

    def run_model(self, trial: Trial) -> None:
        """
        This Script is the one that runs your model. If your model is in the same language
        as your wrapper, you might just directly run it in your wrapper, if it is in
        another language, you might call system commands or start a shell script in
        your wrapper of your language of choice to start your model, or maybe your
        start a batch job to a HPC to be collected later.

        Certain models and wrapper combos have easy access to information about if the model
        succeeded or failed,
        For example, if you are running the model directly in your language
        and not as a batch job, you can do error handling to know if it failed or not.
        If you are running its own process, but also not as a batch job, it often will return
        an exit code to your model and if so, you can use that (0 for success, non 0 for various types
        of errors).
        If this is the case, It might be advised to directly right out your trial_status.json
        file, instead of in a different set_trial_status script. See
        :meth:`~boa.wrappers.script_wrapper.ScriptWrapper.set_trial_status` for formatting and options

        Parameters
        ----------
        trial Trial
        """
        param_names = {metric.name: metric.param_names for metric in self.config.objective.metrics}
        kw = {"param_names": param_names} if param_names else {}
        self._run_subprocess_script_cmd_if_exists(trial, "run_model", **kw)

    def set_trial_status(self, trial: Trial) -> None:
        """
        Marks the status of a trial to reflect the status of the model run for the trial.

        To mark the trial status, first you can write out your data output to a output.json file
        with or without marking the trial status if you are marking as success
        as without the trial_status key as detailed below (if there is no trial_status.json
        file and there is no trial_status key inside the output.json file,
        which is the file that also contains the objective metrics data,
        it will assume it passed since you wrote out data). You can also directly write
        out a trial_status.json file, to do this write out a JSON file of a
        key being trial_status and the value being on of the below trial statuses.
        See below for the proper format.

        Each script is passed a path to the current trial directory as a command line arg,
        that is also the directory you write the json file out to, calling it trial_status.json

        Each trial will be polled periodically to determine its status (completed, failed,
        still running, etc). This function defines the criteria for determining the status
        of the model run for a trial (e.g., whether the model run is completed/still running,
        failed, etc). The trial status is updated accordingly when the trial is polled.

        The approach for determining the trial status will depend on the structure of the
        particular model and its outputs.
        If your model is being ran directly in the same language or as a direct system call and not
        a submission to a batch job system, it might be able to set it easily in
        :meth:`~boa.wrappers.script_wrapper.ScriptWrapper.run_model`
        Other methods can be checking the log files of your model for things like "run complete" and
        "run crashed"
        You can also check for output files, though if your model crashes, it can leave you just waiting
        as it never writes the files. So this is a less ideal option and should be paired with timeouts
        in BOA or your scripts

        Parameters
        ----------
        trial
            something something


        **Relevant ENUM list**

        You can set it to either to text version, or the numerical equivalent

        ==================  =====
        Text                Numerical Equivalent
        ==================  =====
        FAILED                2
        COMPLETED             3
        ABANDONED             4
        EARLY_STOPPED         7
        ==================  =====

        **Format**

        format for trial_status.json file

        .. code-block:: none

            {
                "trial_status": "COMPLETED"
            }


        format for output.json file

        .. code-block:: none

            {
                "obj_metric1": ..., # data for obj_metric1
                "trial_status": "COMPLETED"
            }


        alternative format for output.json file if the trial succeeded you can skip marking it in json file
        (existence is enough to show completion if their is no trial_status file or trial_status key)

        .. code-block:: none

            {
                "obj_metric1": ..., # data for obj_metric1
            }

        See Also
        --------
        :meth:`~boa.wrappers.script_wrapper.ScriptWrapper.run_model`
        # TODO add sphinx link to ax trial status
        """
        param_names = {metric.name: metric.param_names for metric in self.config.objective.metrics}
        kw = {"param_names": param_names} if param_names else {}
        self._run_subprocess_script_cmd_if_exists(trial, "set_trial_status", **kw)
        data = self._read_subprocess_script_output(trial, file_names=["trial_status", "TrialStatus", *OUTPUT_FILES])
        if data is not None:
            trial_status_keys = [k for k in data.keys() if k.lower() == "trialstatus" or k.lower() == "trial_status"]
            if not trial_status_keys:
                data["trial_status"] = "COMPLETED"
                trial_status_keys = ["trial_status"]
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

    def fetch_trial_data(self, trial: Trial, metric_properties: dict, *args, **kwargs) -> dict:
        """
        Retrieves the trial data and prepares it for the metric(s) used in the objective
        function.

        For example, for a case where you are minimizing the error between a model and observations, using RMSE as a
        metric, this function would load the model output and the corresponding observation data that will be passed to
        the RMSE metric.

        The return value of this function is a dictionary, with keys that match the keys
        of the metric used in the objective function.

        .. code-block:: json

            {
                "mean": {
                    "a": [-0.3691, 4.6544, 1.2675, -0.4327]
                }
            }

        We use "mean" as the key in the above example, because we assumed
        the metric that was specified in the config under objectives was mean.
        mean is a wrapper around :external:py:func:`numpy.mean`, which takes as an argument an
        array called a.

        Multiple metrics can be specified for a Multi Objective Optimization,

        .. code-block:: json

            {
                "mean": {
                    "a": [-0.3691, 4.6544, 1.2675, -0.4327]
                },
                "MSE": {
                    "y_true": [1.12, 1.25, 2.54, 4.52]
                    "y_pred": [1.51, 1.01, 2.21, 4.50]
                }
            }

        Parameters
        ----------
        trial : Trial
        metric_properties: dict
            metric_properties specified in configuration file associated with metric
            calling this fetch trial data

        Returns
        -------
        dict
            A dictionary with the keys matching the keys of the metric function
                used in the objective
        """
        param_names = {metric.name: metric.param_names for metric in self.config.objective.metrics}
        kw = {"param_names": param_names} if param_names else {}
        if metric_properties:
            kw["metric_properties"] = metric_properties
        self._run_subprocess_script_cmd_if_exists(
            trial,
            func_names="fetch_trial_data",
            **kw,
        )
        data = self._read_subprocess_script_output(trial, file_names=OUTPUT_FILES)
        if data is not None:
            trial_status_keys = [k for k in data.keys() if k.lower() == "trialstatus" or k.lower() == "trial_status"]
            for key in trial_status_keys:
                data.pop(key)
            return data

    def _run_subprocess_script_cmd_if_exists(self, trial: Trial, func_names: list[str] | str, **kwargs):
        """
        Run a script command from their config file in a subproccess.
        Dump the trial data into a json file for them to collect if need be
        and pass to the script command as a command line argument.

        Parameters
        ----------
        trial : Trial
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
        if isinstance(func_names, str):
            func_names = [func_names]
        ran_cmds = False
        for func_name in func_names:
            run_cmd = getattr(self.config.script_options, func_name)
            if run_cmd:
                ran_cmds = True
                # TODO BaseTrial doesn't have arm property, just arms.
                # With issue #22, fix this to fully support Batched Trials
                trial_dir = save_trial_data(trial, experiment_dir=self.experiment_dir, **kwargs)

                args = split_shell_command(f"{run_cmd} {trial_dir}")
                p = subprocess.Popen(
                    args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE, universal_newlines=True
                )
                # TODO move polling and print to another thread so it doesn't block but still writes to log?
                # Grab stdout line by line as it becomes available.
                # This will loop until p terminates.
                for line in p.stdout:
                    logger.info(line.strip())
        return ran_cmds

    def _read_subprocess_script_output(self, trial: Trial, file_names: Iterable[str] | str):
        trial_dir = get_trial_dir(self.experiment_dir, trial.index)
        if isinstance(file_names, str):
            file_names = [file_names]
        for file_name in file_names:
            output_files = trial_dir.glob(f"{file_name}.*")
            json_output_files = [file for file in output_files if file.suffix.lower() in {".json", ".yml", ".yaml"}]
            if len(json_output_files) > 1:
                raise ValueError(f"{file_name} can only output one json or yaml output file")
            elif len(json_output_files) == 1:
                output_file = json_output_files[0]
                if output_file.exists():
                    return load_jsonlike(output_file)
        return None
