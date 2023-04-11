"""
###################################
Plotting Utils
###################################

Plotting utility functions
"""
from __future__ import annotations

import os
from itertools import combinations
from typing import List, Union

import numpy as np
import pandas as pd
import panel as pn
import plotly.graph_objs as go
from ax.plot.contour import plot_contour_plotly
from ax.plot.helper import get_range_parameters
from ax.plot.pareto_frontier import plot_pareto_frontier as ax_plot_pareto_frontier
from ax.plot.pareto_utils import compute_posterior_pareto_frontier
from ax.plot.slice import interact_slice_plotly
from ax.plot.trace import optimization_trace_single_method_plotly
from ax.service.utils.report_utils import exp_to_df

from boa.definitions import PathLike_tup
from boa.scheduler import Scheduler
from boa.storage import scheduler_from_json_file

SchedulerOrPath = Union[Scheduler, os.PathLike, str]
SchedulersOrPathList = Union[List[Scheduler], List[Union[os.PathLike, str]], Scheduler, os.PathLike, str]


DEFAULT_CI_LEVEL: float = 0.9
pn.extension("plotly")


def _maybe_load_scheduler(scheduler: SchedulerOrPath):
    if isinstance(scheduler, PathLike_tup):
        scheduler = scheduler_from_json_file(scheduler)
    return scheduler


def _maybe_load_schedulers(schedulers: SchedulersOrPathList):
    if not isinstance(schedulers, list):
        schedulers = [schedulers]
    for i, scheduler in enumerate(schedulers):
        schedulers[i] = _maybe_load_scheduler(scheduler)
    return schedulers


def scheduler_to_df(scheduler: SchedulerOrPath, **kwargs) -> pd.DataFrame:
    """
    Transforms an scheduler's experiment to a DataFrame with rows keyed by trial_index
    and arm_name, metrics pivoted into one row. If the pivot results in more than
    one row per arm (or one row per ``arm * map_keys`` combination if ``map_keys`` are
    present), results are omitted and warning is produced.

    Transforms an ``Experiment`` into a ``pd.DataFrame``.

    Parameters
    ----------
    scheduler
        Initialized scheduler or path to `scheduler.json file`.
    **kwargs
        key word arguments to pass to AXs `exp_to_df`

    Returns
    -------
    A dataframe of inputs, metadata and metrics by trial and arm (and
    ``map_keys``, if present). If no trials are available, returns an empty
    dataframe.
    """
    experiment = scheduler.experiment
    return exp_to_df(exp=experiment, **kwargs)


def plot_metrics_trace(
    schedulers: SchedulersOrPathList,
    metric_names: list[str] = None,
    title: str = "Metric Performance vs. # of Iterations",
    **kwargs,
):
    """Plots an optimization trace with mean and 2 SEMs

    Parameters
    ----------
    schedulers
        List of initialized scheduler or path to `scheduler.json file`
        or single initialized scheduler or path to `scheduler.json file`
    metric_names
        metric name or list of metric names to restrict dropdowns to. If None, will use all metric names.
    title
        The title of plot
    **kwargs
        key word arguments to pass to AXs `optimization_trace_single_method_plotly`

    """

    schedulers = _maybe_load_schedulers(schedulers)

    if not metric_names:
        metric_names = list(schedulers[0].experiment.metrics.keys())
    metric_name = pn.widgets.Select(name="Metric Name", options=metric_names)

    def get_plot(metric_name):
        model_transitions = set()
        ys = []
        for scheduler in schedulers:
            data = scheduler.experiment.fetch_data()
            ys.append(data.df[data.df["metric_name"] == metric_name]["mean"])
            model_transitions.update(scheduler.generation_strategy.model_transitions)
        ys = np.array(ys)
        ylabel = metric_name.title()

        return pn.pane.Plotly(
            optimization_trace_single_method_plotly(
                y=ys,
                ylabel=ylabel,
                model_transitions=list(model_transitions),
                # Try and use the metric's lower_is_better property, but fall back on
                # objective's minimize property if relevent
                optimization_direction=(
                    (
                        "minimize"
                        if schedulers[0].experiment.metrics[metric_name].lower_is_better is True
                        else "maximize"
                    )
                    if schedulers[0].experiment.metrics[metric_name].lower_is_better is not None
                    else ("minimize" if schedulers[0].experiment.optimization_config.objective.minimize else "maximize")
                ),
                plot_trial_points=True,
                **kwargs,
            ),
            sizing_mode="stretch_width",
        )

    return pn.Column("## " + title, pn.Row(metric_name), pn.bind(get_plot, metric_name), sizing_mode="stretch_width")


def plot_contours(
    scheduler: SchedulerOrPath,
    metric_names: list[str] = None,
    title: str = "Metric Contours Plot",
    **kwargs,
):
    """Plot predictions for a 2-d slice of the parameter space.

    Parameters
    ----------
    scheduler
        Initialized scheduler or path to `scheduler.json file`.
    metric_names
        metric name or list of metric names to restrict dropdowns to. If None, will use all metric names.
    title
        The title of plot
    **kwargs
        key word arguments to pass to AXs `plot_contour_plotly`
    """
    scheduler = _maybe_load_scheduler(scheduler)

    model = scheduler.generation_strategy.model

    if not metric_names:
        metric_names = list(scheduler.experiment.metrics.keys())

    range_parameters = get_range_parameters(model, min_num_values=5)
    param_names1 = [parameter.name for i, parameter in enumerate(range_parameters) if i != 1]
    param_names2 = [parameter.name for i, parameter in enumerate(range_parameters) if i != 0]

    #     is_log_dict: Dict[str, bool] = {}
    #     grid_dict: Dict[str, np.ndarray] = {}
    #     for parameter in range_parameters:
    #         is_log_dict[parameter.name] = parameter.log_scale
    #         grid_dict[parameter.name] = get_grid_for_parameter(parameter, density)

    # Populate `f_dict` (the predicted expectation value of `metric_name`) and
    # `sd_dict` (the predicted SEM), each of which represents a 2D array of plots
    # where each parameter can be assigned to each of the x or y axes.

    #     f_dict: Dict[str, Dict[str, np.ndarray]] = {
    #         param1: {param2: [] for param2 in param_names} for param1 in param_names
    #     }

    #     sd_dict: Dict[str, Dict[str, np.ndarray]] = {
    #         param1: {param2: [] for param2 in param_names} for param1 in param_names
    #
    metric_name = pn.widgets.Select(name="Metric Name", options=metric_names)

    param_x = pn.widgets.Select(name="Param X", options=param_names1)
    param_y = pn.widgets.Select(name="Param Y", options=param_names2)

    def get_plot(metric_name, param_x, param_y):
        lower_is_better = (
            scheduler.experiment.metrics[metric_name].lower_is_better
            if scheduler.experiment.metrics[metric_name].lower_is_better is not None
            else scheduler.experiment.optimization_config.objective.minimize
        )
        return plot_contour_plotly(
            model=model,
            lower_is_better=lower_is_better,
            param_x=param_x,
            param_y=param_y,
            metric_name=metric_name,
            **kwargs,
        )

    #         plot_data, _, _ = get_plot_data(
    #             model=model, generator_runs_dict=generator_runs_dict, metric_names={metric_name},
    #         )
    #         _, f_plt, sd_plt, _, _, _ = _get_contour_predictions(
    #                 model=model,
    #                 x_param_name=param1,
    #                 y_param_name=param2,
    #                 metric=metric_name,
    #                 generator_runs_dict=generator_runs_dict,
    #                 density=density,
    #                 slice_values=slice_values,
    #                 fixed_features=fixed_features,
    #             )
    #         f_dict[param1][param2] = f_plt
    #         sd_dict[param1][param2] = sd_plt
    #         return pn.Row(f_plt, sd_plt)

    #         return interact_contour_plotly(model=model, metric_name=metric_name, lower_is_better=lower_is_better)

    col = pn.Column(
        "## " + title, pn.Row(metric_name, param_x, param_y), get_plot(metric_name.value, param_x.value, param_y.value)
    )

    def update(event):
        param_x.options = [param.name for param in range_parameters if param.name != param_y.value]
        param_y.options = [param.name for param in range_parameters if param.name != param_x.value]
        print(param_y.options)
        col[-1].object = get_plot(metric_name.value, param_x.value, param_y.value)

    metric_name.param.watch(update, "value")
    param_x.param.watch(update, "value")
    param_y.param.watch(update, "value")

    return col


def plot_slice(scheduler: SchedulerOrPath, **kwargs):
    """Create interactive plot with predictions for a 1-d slice of the parameter
    space.

    Parameters
    ----------
    scheduler
        Initialized scheduler or path to `scheduler.json file`.
    **kwargs
        key word arguments to pass to AXs `interact_slice_plotly`
    """
    scheduler = _maybe_load_scheduler(scheduler)

    model = scheduler.generation_strategy.model
    return pn.pane.Plotly(interact_slice_plotly(model=model, **kwargs))


def plot_pareto_frontier(
    scheduler: SchedulerOrPath,
    metric_names: list[str] | None = None,
    CI_level: float = DEFAULT_CI_LEVEL,  # noqa
):
    """Plot a Pareto frontier from a scheduler.

    Parameters
    ----------
    scheduler
        Initialized scheduler or path to `scheduler.json file`.
    metric_names
        metric name or list of metric names to restrict dropdowns to. If None, will use all metric names.
    CI_level
        The confidence level, i.e. 0.95 (95%)
    """
    scheduler = _maybe_load_scheduler(scheduler)
    experiment = scheduler.experiment
    if metric_names:
        for m in metric_names:
            if m not in scheduler.experiment.metrics:
                raise TypeError(f"metric name {m} not found, check spelling of metric name")
        metric_names = [m for name, m in scheduler.experiment.metrics.items() if name in metric_names]
        metric_combos = combinations(metric_names, 2)

    #     if not metric1 or not metric2:
    #         if len(experiment.metrics) != 2:
    #             raise TypeError(
    #                 "When plotting a pareto frontier, you must either be using a optimization that has exactly"
    #                 " 2 objectives (metrics), or supply your metrics yourself."
    #             )
    #         metric1, metric2 = experiment.metrics.keys()
    else:
        metric_combos = combinations(scheduler.experiment.metrics.values(), 2)

    frontier_list = []
    for ms in metric_combos:
        primary_objective, secondary_objective = ms

        #     try:
        #         primary_objective = experiment.metrics[metric1]
        #     except KeyError as e:
        #         raise TypeError(f"metric name {metric1} not found in optimization!") from e
        #     try:
        #         secondary_objective = experiment.metrics[metric2]
        #     except KeyError as e:
        #         raise TypeError(f"metric name {metric2} not found in optimization!") from e

        frontier = compute_posterior_pareto_frontier(
            experiment=experiment,
            data=experiment.fetch_data(),
            primary_objective=primary_objective,
            secondary_objective=secondary_objective,
            absolute_metrics=[m.name for m in experiment.metrics.values()],
            num_points=30,
        )
        frontier_list.append(frontier)

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
    return pn.pane.Plotly(fig)
