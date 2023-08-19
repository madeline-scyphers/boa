from boa import BaseWrapper, BOAConfig


def test_wrapper_instantiation(generic_config, tmp_path):
    BaseWrapper(config=generic_config, experiment_dir=tmp_path)
