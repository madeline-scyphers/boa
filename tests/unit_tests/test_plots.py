import panel as pn
import plotly.graph_objs as go

from boa.plotting import (
    plot_contours,
    plot_metrics_trace,
    plot_pareto_frontier,
    plot_slice,
)


def test_soo_can_create_plots(branin_main_run):
    scheduler = branin_main_run
    trace = plot_metrics_trace(scheduler)
    assert isinstance(trace, pn.reactive.Reactive)

    contours = plot_contours(scheduler)
    assert isinstance(contours, pn.reactive.Reactive)

    slice = plot_slice(scheduler)
    assert isinstance(slice, pn.reactive.Reactive)


def test_moo_can_create_plots(moo_main_run):
    scheduler = moo_main_run
    pareto_frontier = plot_pareto_frontier(scheduler)
    assert isinstance(pareto_frontier, pn.reactive.Reactive)
