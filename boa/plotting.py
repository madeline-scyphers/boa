from __future__ import annotations

from typing import TypeVar

import numpy as np
import plotly.graph_objs as go
from ax.plot.contour import interact_contour_plotly
from ax.plot.pareto_frontier import plot_pareto_frontier as ax_plot_pareto_frontier
from ax.plot.pareto_utils import compute_posterior_pareto_frontier
from ax.plot.slice import interact_slice_plotly
from ax.plot.trace import optimization_trace_single_method_plotly

from boa.definitions import PathLike_tup
from boa.scheduler import Scheduler
from boa.storage import scheduler_from_json_file

SchedulersOrPath = TypeVar("SchedulersOrPath", Scheduler, *PathLike_tup)
SchedulersOrPathList = TypeVar("SchedulersOrPathList", Scheduler, list[Scheduler], *PathLike_tup)


DEFAULT_CI_LEVEL: float = 0.9


def _maybe_load_scheduler(scheduler: SchedulersOrPath):
    if isinstance(scheduler, PathLike_tup):
        scheduler = scheduler_from_json_file(scheduler)
    return scheduler


def _maybe_load_schedulers(schedulers: SchedulersOrPathList):
    if not isinstance(schedulers, list):
        schedulers = [schedulers]
    for i, scheduler in enumerate(schedulers):
        schedulers[i] = _maybe_load_scheduler(scheduler)
    return schedulers


def plot_single_metric_trace(
    schedulers: SchedulersOrPathList, metric_name: str = None, title: str = "", ylabel: str = None, **kwargs
):

    schedulers = _maybe_load_schedulers(schedulers)

    if not metric_name:
        metric_name = list(schedulers[0].experiment.metrics.keys())[0]
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
        **kwargs,
    )


def plot_contours(scheduler: SchedulersOrPath, metric_name: str = None, **kwargs):
    scheduler = _maybe_load_scheduler(scheduler)

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

        plots += [interact_contour_plotly(model=model, metric_name=name, lower_is_better=lower_is_better)]
    if len(plots) == 1:
        return plots[0]
    return plots


def plot_slice(scheduler: SchedulersOrPath):
    scheduler = _maybe_load_scheduler(scheduler)

    model = scheduler.generation_strategy.model
    return interact_slice_plotly(model=model)


def plot_pareto_frontier(
    scheduler: SchedulersOrPath,
    metric1: str | None = None,
    metric2: str | None = None,
    CI_level: float = DEFAULT_CI_LEVEL,
):
    scheduler = _maybe_load_scheduler(scheduler)
    experiment = scheduler.experiment

    if not metric1 or not metric2:
        if len(experiment.metrics) != 2:
            raise TypeError(
                "When plotting a pareto frontier, you must either be using a optimization that has exactly"
                " 2 objectives (metrics), or supply your metrics yourself."
            )
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
        absolute_metrics=[m.name for m in experiment.metrics.values()],
    )

    frontier_list = [frontier]
    traces = []
    shapes = []
    for frontier in frontier_list:
        config = ax_plot_pareto_frontier(
            frontier=frontier,
            CI_level=CI_level,
        )
        traces.append(config.data["data"][0])
        shapes.append(config.data["layout"].get("shapes", []))

    for i, trace in enumerate(traces):
        if i == 0:  # Only the first trace is initially set to visible
            trace["visible"] = True
        else:  # All other plot traces are not visible initially
            trace["visible"] = False

    # TODO (jej): replace dropdown with two dropdowns, one for x one for y.
    dropdown = []
    for i, frontier in enumerate(frontier_list):
        trace_cnt = 1
        # Only one plot trace is visible at a given time.
        visible = [False] * (len(frontier_list) * trace_cnt)
        for j in range(i * trace_cnt, (i + 1) * trace_cnt):
            visible[j] = True
        rel_y = frontier.primary_metric not in frontier.absolute_metrics
        rel_x = frontier.secondary_metric not in frontier.absolute_metrics
        primary_metric = frontier.primary_metric
        secondary_metric = frontier.secondary_metric
        dropdown.append(
            {
                "method": "update",
                "args": [
                    {"visible": visible, "method": "restyle"},
                    {
                        "yaxis.title": primary_metric,
                        "xaxis.title": secondary_metric,
                        "yaxis.ticksuffix": "%" if rel_y else "",
                        "xaxis.ticksuffix": "%" if rel_x else "",
                        "shapes": shapes[i],
                    },
                ],
                "label": f"{primary_metric} vs {secondary_metric}",
            }
        )

    # Set initial layout arguments.
    initial_frontier = frontier_list[0]
    rel_x = initial_frontier.secondary_metric not in initial_frontier.absolute_metrics
    rel_y = initial_frontier.primary_metric not in initial_frontier.absolute_metrics
    secondary_metric = initial_frontier.secondary_metric
    primary_metric = initial_frontier.primary_metric

    layout = go.Layout(
        title="Pareto Frontier",
        xaxis={
            "title": secondary_metric,
            "ticksuffix": "%" if rel_x else "",
            "zeroline": True,
        },
        yaxis={
            "title": primary_metric,
            "ticksuffix": "%" if rel_y else "",
            "zeroline": True,
        },
        updatemenus=[
            {
                "buttons": dropdown,
                "x": 0.075,
                "xanchor": "left",
                "y": 1.1,
                "yanchor": "middle",
            }
        ],
        hovermode="closest",
        legend={"orientation": "h"},
        width=750,
        height=500,
        margin=go.layout.Margin(pad=4, l=225, b=75, t=75),  # noqa E741
        shapes=shapes[0],
    )

    fig = go.Figure(data=traces, layout=layout)
    return fig
