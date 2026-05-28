import pandas as pd

from boa.ax_api import TrialStatus
from boa.storage import client_from_json_file, client_to_json_file

from behavior_helpers import deterministic_client, deterministic_wrapper


def test_client_run_trials_save_data_and_best_trial_summary(tmp_path):
    client, wrapper = deterministic_client(experiment_dir=tmp_path, n_trials=2)

    client.run_trials(max_trials=2)
    client.save_data(metrics_to_end=True)
    client.report_results()

    assert len(client.experiment.trials) == 2
    assert all(trial.status == TrialStatus.COMPLETED for trial in client.experiment.trials.values())
    assert client.client_filepath.exists()
    assert client.optimization_csv.exists()

    summary = pd.read_csv(client.optimization_csv)
    assert len(summary) == 2
    assert "metric" in summary.columns
    assert client.best_raw_trials() == client.get_best_trials(use_model_predictions=False)
    assert client.wrapper is wrapper


def test_client_json_roundtrip_reattaches_real_wrapper_and_can_continue(tmp_path):
    client, wrapper = deterministic_client(experiment_dir=tmp_path, n_trials=1)
    client.run_trials(max_trials=1)
    client_to_json_file(client, client_filepath="client.json", dir_=tmp_path)

    loaded = client_from_json_file(tmp_path / "client.json", wrapper=wrapper)
    loaded.run_n_trials(1)

    assert loaded.wrapper is wrapper
    assert loaded.experiment.runner.wrapper is wrapper
    assert all(metric.wrapper is wrapper for metric in loaded.experiment.metrics.values() if hasattr(metric, "wrapper"))
    assert len(loaded.experiment.trials) == 2


def test_wrapped_job_runner_runs_real_ax_trial(tmp_path):
    wrapper = deterministic_wrapper(experiment_dir=tmp_path, n_trials=1)
    client = deterministic_client(experiment_dir=tmp_path / "client", n_trials=1)[0]
    client.runner.wrapper = wrapper
    next_trials = client.get_next_trials(max_trials=1)
    trial_index = next(iter(next_trials))
    trial = client.experiment.trials[trial_index]

    run_metadata = client.runner.run(trial)
    statuses = client.runner.poll_trial_status([trial])

    assert run_metadata == {"job_id": trial.index}
    assert statuses[TrialStatus.COMPLETED] == {trial.index}
