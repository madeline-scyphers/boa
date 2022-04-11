

from ax import Experiment, Objective, OptimizationConfig
from ax.service.scheduler import Scheduler, SchedulerOptions
from ax.modelbridge.dispatch_utils import choose_generation_strategy

from utils import get_dictionary_from_callable
from ax_instantiation_utils import instantiate_subspace_from_json
from job_queue import JobQueue
from metrics import FetchMetric
from runner import JobRunner
from fetch_wrapper import read_experiment_config, create_experiment_dir

from pathlib import Path
import click


def make_fetch_experiment_with_runner_and_metric(ex_settings, search_space_params, queue) -> Experiment:

    # Taking command line arguments for path of config file, input data, and output directory

        #use default options if invalid command line arguments are given

    search_space = instantiate_subspace_from_json(search_space_params, [])

    objective=Objective(metric=FetchMetric(name=ex_settings['objective_name'], properties=dict(queue=queue, objective_name=ex_settings["objective_name"])), minimize=True)

    return Experiment(
        search_space=search_space,
        optimization_config=OptimizationConfig(objective=objective),
        runner=JobRunner(queue=queue),
        is_test=True,  # Marking this experiment as a test experiment.
        **get_dictionary_from_callable(Experiment.__init__, ex_settings)
    )


@click.command()
@click.option(
    "-c",
    "--config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=Path("opt_model_config.yml"),
    help="Path to configuration YAML file.",
)
def main(config):
    """This is my docstring

    Args:
        config (os.PathLike): Path to configuration YAML file
    """
    # config_file = "/Users/jmissik/Desktop/repos/fetch3_nhl/optimize/umbs_optimization_config.yml"

    params, ex_settings, model_settings = read_experiment_config(config)  # Read experiment config'
    experiment_dir = create_experiment_dir(ex_settings['working_dir'], ex_settings["experiment_name"])

    queue = JobQueue(params=params, ex_settings=ex_settings, model_settings=model_settings, experiment_dir=experiment_dir)

    experiment = make_fetch_experiment_with_runner_and_metric(ex_settings=ex_settings, search_space_params=params, queue=queue)

    generation_strategy = choose_generation_strategy(
        search_space=experiment.search_space,
        **get_dictionary_from_callable(choose_generation_strategy, ex_settings),
    )


    scheduler = Scheduler(
        experiment=experiment,
        generation_strategy=generation_strategy,
        options=SchedulerOptions(),
    )

    scheduler.run_n_trials(ex_settings["ntrials"])


if __name__ == '__main__':
    main()