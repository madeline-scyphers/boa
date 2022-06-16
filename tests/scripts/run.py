import datetime as dt
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path
from pprint import pformat

from ax.service.utils.report_utils import exp_to_df

try:
    from wrappers import TestWrapper
except ImportError:
    from .wrappers import TestWrapper

from boa import (
    WrappedJobRunner,
    get_experiment,
    get_scheduler,
    get_synth_func,
    load_experiment_config,
    make_experiment_dir,
)


def main(output_dir: os.PathLike = None):
    if output_dir:
        return run_opt(output_dir)
    with tempfile.TemporaryDirectory() as output_dir:
        return run_opt(output_dir)


def run_opt(output_dir):
    print(os.getcwd())
    config_file = Path(__file__).parent / "synth_func_config.yaml"
    start = time.time()
    config = load_experiment_config(config_file)  # Read experiment config'
    experiment_dir = make_experiment_dir(
        output_dir, config["optimization_options"]["experiment_name"]
    )
    # setup the paramb bounds based on the synth func bounds and synth func number of params
    function = get_synth_func(config["model_options"]["function"])
    config["search_space_parameters"] = [
        {"bounds": list(param), "name": f"x{i}", "type": "range", "value_type": "float"}
        for i, param in enumerate(function.domain)
    ]
    # Copy the experiment config to the experiment directory
    shutil.copyfile(config_file, experiment_dir / Path(config_file).name)
    log_format = "%(levelname)s %(asctime)s - %(message)s"
    logging.basicConfig(
        filename=Path(experiment_dir) / "optimization.log",
        filemode="w",
        format=log_format,
        level=logging.DEBUG,
    )
    logging.getLogger().addHandler(logging.StreamHandler())
    logger = logging.getLogger(__file__)
    logger.info("Start time: %s", dt.datetime.now().strftime("%Y%m%dT%H%M%S"))
    wrapper = TestWrapper(
        ex_settings=config["optimization_options"],
        experiment_dir=experiment_dir,
        model_settings=config["model_options"],
    )
    experiment = get_experiment(config, WrappedJobRunner(wrapper=wrapper), wrapper)
    scheduler = get_scheduler(experiment, config=config)
    scheduler.run_all_trials()
    logging.info(pformat(scheduler.get_best_trial()))
    logging.info(scheduler.experiment.fetch_data().df)
    print(pformat(scheduler.get_best_trial()))
    print(scheduler.experiment.fetch_data().df)
    print(exp_to_df(scheduler.experiment))

    logging.info("\nTrials completed! Total run time: %d", time.time() - start)
    return scheduler, config


if __name__ == "__main__":
    main()
