import plotly.graph_objs as go

from boa.plotting import (
    plot_contours,
    plot_pareto_frontier,
    plot_single_metric_trace,
    plot_slice,
)


def test_soo_can_create_plots(branin_main_run):
    scheduler = branin_main_run
    trace = plot_single_metric_trace(scheduler)
    assert isinstance(trace, go.Figure)

    contours = plot_contours(scheduler)
    assert isinstance(contours, go.Figure)

    slice = plot_slice(scheduler)
    assert isinstance(slice, go.Figure)


def test_moo_can_create_plots(moo_main_run):
    scheduler = moo_main_run
    pareto_frontier = plot_pareto_frontier(scheduler)
    assert isinstance(pareto_frontier, go.Figure)
