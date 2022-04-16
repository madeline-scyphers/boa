from __future__ import annotations

from ax import SearchSpace
from ax.service.ax_client import AxClient


def instantiate_subspace_from_json(
    parameters: list | None = None, parameter_constraints: list | None = None
) -> SearchSpace:
    parameters = parameters if parameters is not None else []
    parameter_constraints = parameter_constraints if parameter_constraints is not None else []
    return AxClient.make_search_space(parameters, parameter_constraints)
