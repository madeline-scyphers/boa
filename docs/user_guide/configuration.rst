.. _configuration:

###################
Configuration Guide
###################

***********************
Example Configurations
***********************

Single Objective Optimization
==============================

.. literalinclude:: ../../tests/test_configs/test_config_metric.yaml
    :language: YAML

Multi Objective Optimization
==============================

.. literalinclude:: ../../tests/test_configs/test_config_moo.yaml
    :language: YAML

Additional Configurations
==============================

Example of parameters being specified in alternative ways than the traditional parameters key location.

Useful for if you have multiple sections of parameters that you want to keep logically separated but you are still optimizing over them all, such as different plant species in a multi-species plant model.

.. literalinclude:: ../../tests/test_configs/test_config_param_parse.yaml
    :language: YAML
