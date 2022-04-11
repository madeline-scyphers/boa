from __future__ import annotations
from ax.core.base_trial import BaseTrial, TrialStatus
from fetch_wrapper import create_trial_dir, write_configs, run_model, evaluate, get_trial_dir


class JobQueue:
    """Dummy class to represent a job queue where the Ax `Scheduler` will
    deploy trial evaluation runs during optimization.
    """
    jobs: dict[str, BaseTrial] = {}

    def __init__(self, params, ex_settings, model_settings, experiment_dir):
        self.params = params
        self.ex_settings = ex_settings
        self.model_settings = model_settings
        self.experiment_dir = experiment_dir

    def schedule_job(
        self, trial: int
    ) -> int:
        """Schedules an evaluation job with given parameters and returns job ID."""
        # Code to actually schedule the job and produce an ID would go here;
        # using timestamp as dummy ID for this example.
        trial_dir = create_trial_dir(self.experiment_dir, trial.index)

        # self.modelfile = trial_dir / ex_settings['output_fname'] # model output

        config_dir = write_configs(trial_dir, trial.arm.parameters, self.model_settings)

        run_model(self.ex_settings['model_path'], config_dir, self.ex_settings['data_path'], trial_dir)

        # self.jobs[trial.index] = Job(trial.index, trial.arm.parameters, trial_dir)
        self.jobs[trial.index] = trial

        return trial.index


    def get_job_status(self, trial: int) -> TrialStatus:
        """ "Get status of the job by a given ID. For simplicity of the example,
        return an Ax `TrialStatus`.
        """
        # Instead of randomizing trial status, code to check actual job status
        # would go here.
        log_file = get_trial_dir(self.experiment_dir, trial.index) / "fetch3.log"
        # log_file = Path("/Users/madelinescyphers/projs/optiwrap/output/fetch_UMBS_test_oak_20220411T093217") / "000000/fetch3.log"

        if log_file.exists():
            with open(log_file, "r") as f:
                contents = f.read()
            if "run complete" in contents:
                self.jobs[trial.index].mark_completed()

        return self.jobs[trial.index].status

    def get_outcome_value_for_completed_job(self, job_id: int) -> dict[str, float]:
        """Get evaluation results for a given completed job."""
        # In a real external system, this would retrieve real relevant outcomes and
        # not a synthetic function value.

        modelfile =  get_trial_dir(self.experiment_dir, job_id) / self.ex_settings['output_fname']

        data = evaluate(modelfile=modelfile, obsfile=self.ex_settings['obsfile'], ex_settings=self.ex_settings, model_settings=self.model_settings, params=self.jobs[job_id].arm.parameters)
        return data
