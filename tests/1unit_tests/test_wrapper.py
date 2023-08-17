from boa import BaseWrapper, BOAConfig


def test_wrapper_instantiation(generic_config):
    BaseWrapper(config=generic_config)
