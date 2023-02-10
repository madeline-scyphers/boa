from __future__ import  annotations

from typing import TypeVar

from ax.plot.trace import optimization_trace_single_method_plotly
from ax.service.utils.report_utils import get_standard_plots, exp_to_df
from ax.plot.slice import interact_slice_plotly
from ax.plot.contour import interact_contour_plotly
from ax.plot.pareto_frontier import interact_pareto_frontier
from ax.plot.pareto_utils import compute_posterior_pareto_frontier
import numpy as np

from boa.scheduler import Scheduler
from boa.storage import scheduler_from_json_file
from boa.definitions import PathLike, PathLike_tup


SchedulersOrPath = TypeVar("SchedulersOrPath", Scheduler, *PathLike_tup)
SchedulersOrPathList = TypeVar("SchedulersOrPathList", Scheduler, list[Scheduler], *PathLike_tup)


def maybe_load_scheduler(scheduler: SchedulersOrPath):
    if isinstance(scheduler, PathLike_tup):
        scheduler = scheduler_from_json_file(scheduler)
    return scheduler


def maybe_load_schedulers(schedulers: SchedulersOrPathList):
    if not isinstance(schedulers, list):
        schedulers = [schedulers]
    for i, scheduler in enumerate(schedulers):
        schedulers[i] = maybe_load_scheduler(scheduler)
    return schedulers


def single_metric_trace(
        schedulers: SchedulersOrPathList,
        metric_name: str = None,
        title: str = "",
        ylabel: str = None,
        **kwargs
):

    schedulers = maybe_load_schedulers(schedulers)

    if not metric_name:
        metric_name = list(schedulers[0].experiment.metrics.keys())[0]
    # ys = np.array([[1.2, 2.2, 3.1], [1.3, 2.0, 2.5], [1.8, 1.9, 2.8]])
    model_transitions = set()
    ys = []
    for scheduler in schedulers:
        data = scheduler.experiment.fetch_data()
        ys.append(data.df[data.df["metric_name"] == metric_name]["mean"])
        model_transitions.update(scheduler.generation_strategy.model_transitions)
    ys = np.array(ys)

    if ylabel is None:
        ylabel = metric_name.title()

    return optimization_trace_single_method_plotly(
        y=ys,
        title=title,
        ylabel=ylabel,
        model_transitions=model_transitions,
        # Try and use the metric's lower_is_better property, but fall back on
        # objective's minimize property if relevent
        optimization_direction=(
            ("minimize" if schedulers[0].experiment.metrics[metric_name].lower_is_better is True else "maximize")
            if schedulers[0].experiment.metrics[metric_name].lower_is_better is not None
            else ("minimize" if schedulers[0].experiment.optimization_config.objective.minimize else "maximize")
        ),
        plot_trial_points=True,
        **kwargs
    )


def interact_contours(
        scheduler: SchedulersOrPath,
        metric_name: str = None,
        **kwargs
):
    scheduler = maybe_load_scheduler(scheduler)

    model = scheduler.generation_strategy.model
    if not metric_name:
        metric_name = model.metric_names

    if isinstance(metric_name, str):
        metric_name = [metric_name]

    plots = []
    for name in metric_name:
        lower_is_better = (
            scheduler.experiment.metrics[name].lower_is_better
            if scheduler.experiment.metrics[name].lower_is_better is not None
            else scheduler.experiment.optimization_config.objective.minimize
        )

        plots += [
            interact_contour_plotly(
                model=model,
                metric_name=name,
                lower_is_better=lower_is_better
            )
            ]
    if len(plots) == 1:
        return plots[0]
    return plots


def interact_slice(scheduler: SchedulersOrPath):
    scheduler = maybe_load_scheduler(scheduler)

    model = scheduler.generation_strategy.model
    return interact_slice_plotly(model=model)


def plot_pareto_frontier(
        scheduler: SchedulersOrPath,
        metric1: str | None = None,
        metric2: str | None = None,
):
    scheduler = maybe_load_scheduler(scheduler)
    experiment = scheduler.experiment

    if not metric1 or not metric2:
        if len(experiment.metrics) != 2:
            raise TypeError("When plotting a pareto frontier, you must either be using a optimization that has exactly"
                            " 2 objectives (metrics), or supply your metrics yourself.")
        metric1, metric2 = experiment.metrics.keys()

    try:
        primary_objective = experiment.metrics[metric1]
    except KeyError as e:
        raise TypeError(f"metric name {metric1} not found in optimization!") from e
    try:
        secondary_objective = experiment.metrics[metric2]
    except KeyError as e:
        raise TypeError(f"metric name {metric2} not found in optimization!") from e

    frontier = compute_posterior_pareto_frontier(
        experiment=experiment,
        primary_objective=primary_objective,
        secondary_objective=secondary_objective,
        absolute_metrics=[m.name for m in experiment.metrics.values()]
    )

    return interact_pareto_frontier(
        frontier_list=[frontier]
    )
