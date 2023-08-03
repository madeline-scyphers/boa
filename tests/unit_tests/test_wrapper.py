from boa import BaseWrapper, Config


def test_wrapper_instantiation(generic_config):
    BaseWrapper(config=Config(**generic_config))
