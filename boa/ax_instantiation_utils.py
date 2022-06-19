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
from ax.service.ax_client import AxClient
from ax.service.scheduler import Scheduler, SchedulerOptions

from boa.metrics.metrics import get_metric_from_config
from boa.utils import get_dictionary_from_callable


def instantiate_search_space_from_json(
    parameters: list | None = None, parameter_constraints: list | None = None
) -> SearchSpace:
    parameters = parameters if parameters is not None else []
    parameter_constraints = parameter_constraints if parameter_constraints is not None else []
    return AxClient.make_search_space(parameters, parameter_constraints)


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
        config.get("search_space_parameters"), config.get("search_space_parameter_constraints")
    )

    optimization_config = get_optimization_config(
        opt_options, wrapper, list(search_space.parameters)
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


def get_optimization_config(
    config, wrapper=None, param_names=None
) -> OptimizationConfig | MultiObjectiveOptimizationConfig:
    if "scalarized_objective_options" in config:
        objective_options = config["scalarized_objective_options"]
        metrics = []
        weights = []
        kw = {}
        outcome_constraints = []
        for objective_opts in objective_options["objectives"]:
            if "weight" in objective_opts:
                weights.append(objective_opts["weight"])
            metric = get_metric_from_config(
                objective_opts, wrapper=wrapper, param_names=param_names
            )
            metrics.append(metric)
        if weights:
            kw["weights"] = weights
        if "minimize" in objective_opts:
            kw["minimize"] = objective_opts["minimize"]
        objective = ScalarizedObjective(metrics=metrics, **kw)
    # if config.get("objective_options"):
    #     objective_options = config["objective_options"]
    #     objectives = []
    #     objective_thresholds = []
    #     outcome_constraints = []
    #     for options in objective_options:
    #         metric = get_metric_from_config(options, wrapper=wrapper, param_names=param_names)
    #         objectives.append(Objective(metric=metric))
    #
    #         outcome_kw = options.get("outcome_constraints", {})
    #         op = outcome_kw.get("op", "")
    #         op = ComparisonOp(op)
    #
    #         outcome_constraints.append(OutcomeConstraint(metric=metric, op=op, **outcome_kw),)
    #         objective_thresholds.append(ObjectiveThreshold(metric=metric, **options.get("objective_thresholds", {})))
    #
    #     if len(objectives) > 1:
    #         objective = MultiObjective(objectives)
    #
    #         opt_conf = MultiObjectiveOptimizationConfig(
    #             objective=objective,
    #             outcome_constraints=outcome_constraints,
    #             objective_thresholds=objective_thresholds,
    #         )
    #     else:
    #         objective = Objective(metric=metric)
    #         opt_conf = OptimizationConfig(objective=objective)

    else:
        metric = get_metric_from_config(config["metric"], wrapper=wrapper, param_names=param_names)
        objective = Objective(metric=metric)
    opt_conf = OptimizationConfig(objective=objective)

    return opt_conf
