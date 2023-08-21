import pytest

from boa import BaseWrapper as BWrapper
from boa import ModularMetric as MMetric
from boa import WrappedJobRunner as WRunner


def test_wrapper_instantiation(generic_config, tmp_path):
    BWrapper(config=generic_config, experiment_dir=tmp_path)


def test_creating_wrapper_with_same_name_as_other_wrapper_from_diff_file_raises_val_error_and_metric_and_runner():
    with pytest.raises(ValueError):

        class BaseWrapper(BWrapper):
            pass

    with pytest.raises(ValueError):

        class ModularMetric(MMetric):
            pass

    with pytest.raises(ValueError):

        class WrappedJobRunner(WRunner):
            pass
