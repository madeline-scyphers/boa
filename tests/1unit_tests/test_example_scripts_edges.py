from pathlib import Path

import boa.scripts.moo as moo
import boa.scripts.run_branin as run_branin
import boa.scripts.script_wrappers as script_wrappers
from boa import get_client, get_trial_dir
from boa.ax_api import TrialStatus
from boa.definitions import ROOT


def test_branin_wrapper_runs_real_script_and_fetches_output(tmp_path):
    wrapper = script_wrappers.BraninWrapper(
        config_path=ROOT / "boa/scripts/synth_func_config.yaml",
        experiment_dir=tmp_path,
    )
    client = get_client(config=wrapper.config, wrapper=wrapper)
    trial_index = next(iter(client.get_next_trials(1)))
    trial = client.experiment.trials[trial_index]

    wrapper.run_model(trial)
    process = wrapper._processes[-1]
    assert process.wait(timeout=20) == 0

    wrapper.set_trial_status(trial)
    assert trial.status == TrialStatus.COMPLETED

    fetched = wrapper.fetch_trial_data(trial)
    assert len(fetched["y_pred"]) == wrapper.model_settings["input_size"]
    assert len(fetched["y_true"]) == wrapper.model_settings["input_size"]
    assert (get_trial_dir(wrapper.experiment_dir, trial.index) / "output.json").exists()


def test_script_wrapper_exit_handler_kills_registered_process():
    process = script_wrappers.subprocess.Popen(["python", "-c", "import time; time.sleep(60)"])
    try:
        script_wrappers.BraninWrapper._processes = [process]
        script_wrappers.exit_handler()
        assert process.wait(timeout=20) is not None
    finally:
        script_wrappers.BraninWrapper._processes = []
        if process.poll() is None:
            process.kill()
            process.wait(timeout=20)


def test_run_branin_run_opt_returns_real_client(tmp_path):
    client = run_branin.run_opt(tmp_path)

    assert client.wrapper is not None
    assert client.client_filepath.exists()
    assert client.optimization_csv.exists()
    assert len(client.experiment.trials) == client.wrapper.config.trials - 5
    assert {trial.status for trial in client.experiment.trials.values()} == {TrialStatus.COMPLETED}


def test_moo_wrapper_fetches_real_synthetic_function(tmp_path):
    wrapper = moo.WrapperMoo(config_path=Path(moo.__file__).resolve().parent / "moo.yaml", experiment_dir=tmp_path)
    client = get_client(config=wrapper.config, wrapper=wrapper)
    trial_index = next(iter(client.get_next_trials(1)))
    trial = client.experiment.trials[trial_index]

    result = wrapper.fetch_trial_data(trial, {}, "branin", parameters=trial.arm.parameters)

    assert set(result) == {"branin", "currin"}
    assert all(isinstance(value, float) for value in result.values())


def test_moo_main_runs_real_controller():
    client = moo.main()

    assert client.wrapper is not None
    assert client.experiment.optimization_config.is_moo_problem
    assert {"branin", "currin"}.issubset(client.experiment.metrics)
    assert len(client.experiment.trials) == client.wrapper.config.trials
