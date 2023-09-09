import shutil
import sys

import numpy as np
import pandas as pd
import pytest
from numpy.testing import assert_almost_equal
from pandas.testing import assert_frame_equal

from boa import split_shell_command
from boa.async_opt import main
from boa.definitions import PathLike
from tests.conftest import TEST_CONFIG_DIR

rng = np.random.default_rng()


def update_opt_csv(opt_csv: PathLike, vals: dict):
    df = pd.read_csv(opt_csv)
    nan_rows = df.isna().any(axis=1)
    metrics = list(vals.keys())
    df2 = pd.DataFrame(vals)
    assert nan_rows.sum() == len(df2)
    df.loc[nan_rows, metrics] = df2.values  # we use .values to avoid index mismatch
    df.to_csv(opt_csv, index=False)


def exp_val_vs_ins_val(exp_df: pd.DataFrame, inserted_vals: dict):
    last_trial_idx = exp_df["trial_index"].max()
    for metric, vals in inserted_vals.items():
        n_inserted = len(vals)
        for i, inserted_value in enumerate(vals):
            trial_idx = last_trial_idx - (n_inserted - 1) + i
            trial_mask = exp_df["trial_index"] == trial_idx
            metric_mask = exp_df["metric_name"] == metric
            exp_value = exp_df.loc[trial_mask & metric_mask, "mean"].iloc[0]
            assert_almost_equal(exp_value, inserted_value)


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Windows doesn't support moving files that are open")
@pytest.mark.parametrize(
    "config_path",
    [
        TEST_CONFIG_DIR / "test_config_pass_through_metric.yaml",  # no explicit gen strat defined in config
        TEST_CONFIG_DIR / "test_config_generic.yaml",  # explicit gen strat defined in config
    ],
)
def test_async(config_path, tmp_path):
    n_ran_trials = 0
    n = 5  # pass in n to see if we can override the config
    # use -td to run in temp dir and not pollute the repo
    scheduler = main(split_shell_command(f"-c {config_path} -n {n} -td"), standalone_mode=False)
    n_ran_trials += n
    assert scheduler.experiment.num_trials == n_ran_trials

    vals1 = {metric: rng.random(n) for metric in scheduler.experiment.metrics.keys()}
    update_opt_csv(scheduler.opt_csv, vals1)

    n = 7
    scheduler = main(split_shell_command(f"-sp {scheduler.scheduler_filepath} -n {n}"), standalone_mode=False)
    n_ran_trials += n
    assert scheduler.experiment.num_trials == n_ran_trials
    exp_df = scheduler.experiment.fetch_data().df
    exp_val_vs_ins_val(exp_df=exp_df, inserted_vals=vals1)

    vals2 = {metric: np.arange(0, n) for metric in scheduler.experiment.metrics.keys()}
    update_opt_csv(scheduler.opt_csv, vals2)

    output_dir = tmp_path / "output_dir"
    shutil.move(scheduler.scheduler_filepath.parent, output_dir)
    output_dir / "scheduler.json"

    n = 12
    scheduler = main(split_shell_command(f"-sp {output_dir / 'scheduler.json'} -n {n}"), standalone_mode=False)
    n_ran_trials += n
    assert scheduler.experiment.num_trials == n_ran_trials
    exp_df = scheduler.experiment.fetch_data().df
    exp_val_vs_ins_val(exp_df=exp_df, inserted_vals=vals2)

    df = pd.DataFrame(
        {metric_name: np.concatenate((value, vals2[metric_name])) for metric_name, value in vals1.items()}
    )
    df = (
        df.stack()  # stack to get metric_name and trial index as indexes
        .reset_index()  # move metric_name and trial index to a column
        .rename(columns={"level_1": "metric_name", "level_0": "trial_index", 0: "mean"})
    )  # rename the columns

    assert_frame_equal(
        df.reset_index(drop=True),  # remove index to avoid index mismatch, we don't care about the index
        (
            exp_df[df.columns]  # only compare the columns we care about
            .sort_values(by=df.columns.to_list())  # sort by all columns to make sure the order is the same
            .reset_index(drop=True)
        ),  # remove index to avoid index mismatch, we don't care about the index
    )
