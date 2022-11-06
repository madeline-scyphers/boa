import sys

import numpy as np
import pytest
from ax import Experiment, Objective, OptimizationConfig

from boa import (
    ModularMetric,
    WrappedJobRunner,
    cd_and_cd_back,
    get_dictionary_from_callable,
    get_scheduler,
    instantiate_search_space_from_json,
    scheduler_from_json_file,
    scheduler_to_json_file,
)
from boa.definitions import ROOT


@pytest.mark.skip(reason="Scheduler can't be saved with generic callable yet")
def test_save_load_scheduler(metric_config, tmp_path):
    p = (ROOT / "tests/scripts/stand_alone_opt_package").resolve()
    sys.path.append(p)

    from tests.scripts.stand_alone_opt_package.wrapper import Wrapper

    with cd_and_cd_back(p):
        scheduler_json = tmp_path / "scheduler.json"
        config = metric_config
        opt_options = config["optimization_options"]

        wrapper = Wrapper()
        wrapper.config = config
        wrapper.mk_experiment_dir(experiment_dir=tmp_path, append_timestamp=False)

        runner = WrappedJobRunner(wrapper=wrapper)
        search_space = instantiate_search_space_from_json(config.get("parameters"), config.get("parameter_constraints"))

        optimization_config = OptimizationConfig(Objective(ModularMetric(metric_to_eval=np.median), minimize=True))

        experiment = Experiment(
            search_space=search_space,
            optimization_config=optimization_config,
            runner=runner,
            **get_dictionary_from_callable(Experiment.__init__, opt_options["experiment"]),
        )
        scheduler = get_scheduler(experiment=experiment, config=config)

        assert "median" in scheduler.experiment.metrics

        scheduler_to_json_file(scheduler, scheduler_json)

        scheduler = scheduler_from_json_file(scheduler_json, wrapper=wrapper)

        assert "median" in scheduler.experiment.metrics
