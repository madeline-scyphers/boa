from __future__ import annotations

import copy
import time

from ax import (
    ComparisonOp,
    Experiment,
    MultiObjective,
    MultiObjectiveOptimizationConfig,
    Objective,
    ObjectiveThreshold,
    OptimizationConfig,
    OutcomeConstraint,
    Runner,
    SearchSpace,
)
from ax.core.objective import ScalarizedObjective
from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.modelbridge.generation_strategy import GenerationStep, GenerationStrategy
from ax.modelbridge.registry import Models
from ax.service.scheduler import Scheduler, SchedulerOptions

from boa.metrics.metrics import get_metric_from_config
from boa.utils import get_dictionary_from_callable
from boa.instantiation_base import BoaInstantiationBase


def instantiate_search_space_from_json(
    parameters: list | None = None, parameter_constraints: list | None = None
) -> SearchSpace:
    parameters = parameters if parameters is not None else []
    parameter_constraints = parameter_constraints if parameter_constraints is not None else []
    return BoaInstantiationBase.make_search_space(parameters, parameter_constraints)


def get_generation_strategy(config: dict, experiment: Experiment = None):
    if config.get(
        "steps"
    ):  # if they are explicitly defining the steps, use those to make gen strat
        return generation_strategy_from_config(config=config, experiment=experiment)
    # else auto generate the gen strat
    return choose_generation_strategy_from_experiment(experiment=experiment, config=config)


def generation_strategy_from_config(config: dict, experiment: Experiment = None):
    config_ = copy.deepcopy(config)
    for i, step in enumerate(config_["steps"]):
        try:
            step["model"] = Models[step["model"]]
        except KeyError:
            step["model"] = Models(step["model"])
        config_["steps"][i] = GenerationStep(**step)

    gs = GenerationStrategy(**get_dictionary_from_callable(GenerationStrategy.__init__, config_))
    if experiment:
        gs.experiment = experiment
    return gs


def choose_generation_strategy_from_experiment(
    experiment: Experiment, config: dict
) -> GenerationStrategy:
    return choose_generation_strategy(
        search_space=experiment.search_space,
        **get_dictionary_from_callable(choose_generation_strategy, config),
    )


def get_scheduler(
    experiment: Experiment,
    generation_strategy: GenerationStrategy = None,
    scheduler_options: SchedulerOptions = None,
    config: dict = None,
):
    scheduler_options = scheduler_options or SchedulerOptions(
        **config["optimization_options"]["scheduler"]
    )
    if generation_strategy is None:
        if (
            "total_trials" in config["optimization_options"]["scheduler"]
            and "num_trials" not in config["optimization_options"]["generation_strategy"]
        ):
            config["optimization_options"]["generation_strategy"]["num_trials"] = config[
                "optimization_options"
            ]["scheduler"]["total_trials"]
        generation_strategy = get_generation_strategy(
            config=config["optimization_options"]["generation_strategy"], experiment=experiment
        )
    # db_settings = DBSettings(
    #     url="sqlite:///foo.db",
    #     decoder=Decoder(config=SQAConfig()),
    #     encoder=Encoder(config=SQAConfig()),
    # )

    # init_engine_and_session_factory(url=db_settings.url)
    # engine = get_engine()
    # create_all_tables(engine)

    return Scheduler(
        experiment=experiment,
        generation_strategy=generation_strategy,
        options=scheduler_options,
        # db_settings=db_settings,
    )


def get_experiment(
    config: dict,
    runner: Runner,
    wrapper=None,
):
    opt_options = config["optimization_options"]

    search_space = instantiate_search_space_from_json(
        config.get("parameters"), config.get("parameter_constraints")
    )

    optimization_config = BoaInstantiationBase.make_optimization_config(
        **get_dictionary_from_callable(
            BoaInstantiationBase.make_optimization_config, opt_options["objective_options"]
        ),
        wrapper=wrapper,
    )

    if "name" not in opt_options["experiment"]:
        if "name" in opt_options:
            opt_options["experiment"]["name"] = opt_options["name"]
        else:
            opt_options["experiment"]["name"] = time.time()

    return Experiment(
        search_space=search_space,
        optimization_config=optimization_config,
        runner=runner,
        **get_dictionary_from_callable(Experiment.__init__, opt_options["experiment"]),
    )
