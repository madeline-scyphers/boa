
import subprocess
import os

from ax import Trial

from optiwrap import (
    BaseWrapper,
    cd_and_cd_back,
    get_trial_dir,
    make_trial_dir,
    write_configs,
)

import pandas as pd
import numpy as np
import xarray as xr

def get_model_obs(modelfile, obsfile, ex_settings, model_settings, parameters):
    """
    Read in observation data model output for a trial, which will be used for
    calculating the objective function for the trial.

    Parameters
    ----------
    modelfile : str
        File path to the model output
    obsfile : str
        File path to the observation data
    model_settings: dict
        dictionary with model settings read from model config file

    Returns
    -------
    model_output: pandas Series
        Model output
    obs: pandas Series
        Observations

    ..todo::
        * Add options to specify certain variables from the observation/output files
        * Add option to read from .nc file

    """
    #Read config file

    # Read in observation data
    obsdf = pd.read_csv(obsfile, parse_dates = [0])
    obsdf = obsdf.set_index('Timestamp')
    # metdf.index = metdf.index - pd.to_timedelta('30Min') # TODO: remove timestamp shift

    # Read in model output
    modeldf = xr.load_dataset(modelfile)


    # Slice met data to just the time period that was modeled
    obsdf = obsdf.loc[modeldf.time.data[0]:modeldf.time.data[-1]]

    # Convert model output to the same units as the input data
    # modeldf['sapflux_scaled'] = scale_sapflux(modeldf.sapflux, model_settings['dz'],
    #                                               parameters['mean_crown_area_sp'],
    #                                               parameters['total_crown_area_sp'],
    #                                               parameters['plot_area'])
    modeldf['trans_scaled'] = scale_transpiration(modeldf.trans_2d, model_settings['dz'],
                                                  parameters['mean_crown_area_sp'],
                                                  parameters['total_crown_area_sp'],
                                                  parameters['plot_area'])

    # remove first and last timestamp
    obsdf = obsdf.iloc[1:-1]
    modeldf = modeldf.trans_scaled.isel(time=np.arange(1,len(modeldf.time)-1))

    return modeldf.data, obsdf[ex_settings['obsvar']]

def scale_sapflux(sapflux, dz, mean_crown_area_sp, total_crown_area_sp, plot_area):
    """Scales sapflux from FETCH output (in kg s-1) to W m-2"""
    scaled_sapflux = (sapflux * 2440000 /
                        mean_crown_area_sp * total_crown_area_sp
                        / plot_area)
    return scaled_sapflux

def scale_transpiration(trans, dz, mean_crown_area_sp, total_crown_area_sp, plot_area):
    """Scales transpiration from FETCH output (in m H20 m-2crown m-1stem s-1) to W m-2"""
    scaled_trans = (trans * 1000 * dz * 2440000 * total_crown_area_sp
                        / plot_area).sum(dim='z', skipna=True)
    return scaled_trans

def ssqr(model, obs):
    """
    Sum of squares objective function (model vs observation)

    Parameters
    ----------
    model : pandas series
        Model output
    obs : pandas series
        Observation data

    Returns
    -------
    float
        Mean sum of squares for (model - observations)
    """
    return ((model - obs) ** 2).mean()

def evaluate(modelfile, obsfile, ex_settings, model_settings, params):
    """
    Defines how to evaluate trials.

    Parameters
    ----------
    modelfile : Path
        File with model output
    obsfile : Path
        File with observation data

    Returns
    -------
    dict
        Dict with definition of objective function
    """
    model, obs = get_model_obs(modelfile, obsfile, ex_settings, model_settings, params)
    return {"ssqr": ssqr(model, obs)}




class Fetch3Wrapper(BaseWrapper):
    def __init__(self, ex_settings, model_settings, experiment_dir, main_prog=""):
        self.ex_settings = ex_settings
        self.model_settings = model_settings
        self.experiment_dir = experiment_dir
        self.main_prog = main_prog

    def run_model(self, trial: Trial):

        trial_dir = make_trial_dir(self.experiment_dir, trial.index)

        config_dir = write_configs(trial_dir, trial.arm.parameters, self.model_settings)

        model_path = self.ex_settings["model_path"]

        os.chdir(model_path)

        # with cd_and_cd_back(model_path):
        args = [
            "python3",
            f"main{self.main_prog}.py",
            "--config_path",
            str(config_dir),
            "--data_path",
            str(self.ex_settings["data_path"]),
            "--output_path",
            str(trial_dir),
        ]
        result = subprocess.run(
            args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )

        print(result.stdout)
        print(result.stderr)
        print("Done running model")

    def set_trial_status(self, trial: Trial) -> None:
        """ "Get status of the job by a given ID. For simplicity of the example,
        return an Ax `TrialStatus`.
        """
        log_file = get_trial_dir(self.experiment_dir, trial.index) / "fetch3.log"

        if log_file.exists():
            with open(log_file, "r") as f:
                contents = f.read()
            if "run complete" in contents:
                trial.mark_completed()

    def fetch_trial_data(self, trial: Trial, *args, **kwargs):

        modelfile = (
            get_trial_dir(self.experiment_dir, trial.index) / self.ex_settings["output_fname"]
        )

        y_pred, y_true = get_model_obs(
            modelfile,
            self.ex_settings["obsfile"],
            self.ex_settings,
            self.model_settings,
            trial.arm.parameters,
        )
        return dict(y_pred=y_pred, y_true=y_true)


class Fetch3Wrapper2(Fetch3Wrapper):

    def fetch_trial_data(self, trial: Trial, *args, **kwargs):

        filename = (
            get_trial_dir(self.experiment_dir, trial.index) / "output.json"
        )
        path_to_data = ["mse"]

        return dict(val=12)

        return dict(filename=filename, path_to_data=path_to_data)