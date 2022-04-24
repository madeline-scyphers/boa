
import subprocess

from ax import Trial

from optiwrap import (
    BaseWrapper,
    cd_and_cd_back,
    get_model_obs,
    get_trial_dir,
    make_trial_dir,
    write_configs,
)


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

        with cd_and_cd_back(model_path):
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