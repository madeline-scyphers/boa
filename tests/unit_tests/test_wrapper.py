from boa import BaseWrapper, BOAConfig


def test_wrapper_instantiation(generic_config):
    BaseWrapper(config=BOAConfig(**generic_config))
