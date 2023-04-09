import json
import sys

import numpy as np
import pytest
from ax import Experiment, Objective, OptimizationConfig

import boa.__main__ as dunder_main
from boa import (
    ModularMetric,
    WrappedJobRunner,
    cd_and_cd_back,
    get_dictionary_from_callable,
    get_scheduler,
    instantiate_search_space_from_json,
    scheduler_from_json_file,
    scheduler_to_json_file,
    split_shell_command,
)
from boa.__version__ import __version__
from boa.definitions import ROOT

TEST_DIR = ROOT / "tests"


def test_save_load_scheduler_branin(branin_main_run, tmp_path):
    file_out = tmp_path / "scheduler.json"
    scheduler = branin_main_run
    config = scheduler.runner.wrapper.config
    scheduler_to_json_file(scheduler, file_out)

    pre_num_trials = len(scheduler.experiment.trials)

    scheduler = scheduler_from_json_file(file_out)
    scheduler.run_n_trials(5)

    post_num_trials = len(scheduler.experiment.trials)

    # assert some trials run, even if we hit max trials and not all specified trials were run
    assert post_num_trials > pre_num_trials


def test_can_pass_custom_wrapper_path_when_loading_scheduler(branin_main_run, tmp_path):
    file_out = tmp_path / "scheduler.json"
    scheduler = branin_main_run

    orig_wrapper_path = scheduler.experiment.runner.wrapper._path
    scheduler.experiment.runner.wrapper._path = "SOME/OTHER/PATH"

    scheduler_to_json_file(scheduler, file_out)

    pre_num_trials = len(scheduler.experiment.trials)

    scheduler = scheduler_from_json_file(file_out, wrapper_path=orig_wrapper_path)
    scheduler.run_n_trials(5)

    post_num_trials = len(scheduler.experiment.trials)

    # assert some trials run, even if we hit max trials and not all specified trials were run
    assert post_num_trials > pre_num_trials


def test_can_pass_custom_wrapper_path_when_loading_scheduler_from_cli(stand_alone_opt_package_run, tmp_path_factory):
    scheduler = stand_alone_opt_package_run
    wrapper = scheduler.experiment.runner.wrapper

    temp_dir = tmp_path_factory.mktemp("temp_dir")
    file_out = temp_dir / "scheduler.json"

    orig_wrapper_path = scheduler.experiment.runner.wrapper._path
    scheduler.experiment.runner.wrapper._path = "SOME/OTHER/PATH"

    scheduler_to_json_file(scheduler, file_out)

    pre_num_trials = len(scheduler.experiment.trials)

    scheduler = dunder_main.main(
        split_shell_command(f"--scheduler-path {file_out} --wrapper-path {orig_wrapper_path} -td"),
        standalone_mode=False,
    )

    scheduler.run_n_trials(5)

    post_num_trials = len(scheduler.experiment.trials)

    # assert some trials run, even if we hit max trials and not all specified trials were run
    assert post_num_trials > pre_num_trials


def test_boa_version_in_scheduler(stand_alone_opt_package_run, tmp_path_factory):
    scheduler = stand_alone_opt_package_run

    temp_dir = tmp_path_factory.mktemp("temp_dir")
    file_out = temp_dir / "scheduler.json"

    scheduler_to_json_file(scheduler, file_out)
    with open(file_out, "r") as f:
        scheduler_json = json.load(f)

    assert "boa_version" in scheduler_json
    assert scheduler_json["boa_version"] == __version__


@pytest.mark.skip(reason="Scheduler can't be saved with generic callable yet")
def test_save_load_scheduler_with_generic_callable(metric_config, tmp_path):
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
