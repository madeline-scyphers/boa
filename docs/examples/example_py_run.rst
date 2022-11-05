########################################################
Running an Experiment from Command Line (Python Wrapper)
########################################################

This is a small toy example to showcase how to start a Experiment with a Wrapper in Python from command line

Given a Python wrapper:

*wrapper.py*

.. literalinclude:: ../../tests/scripts/stand_alone_opt_package/wrapper.py
    :language: python

and some "model" it is running (in this case it is just calling a synthetic function in python):

*stand_alone_model_func.py*

.. literalinclude:: ../../tests/scripts/stand_alone_opt_package/stand_alone_model_func.py
    :language: python

as well as a configuration file:

*config.py*

.. literalinclude:: single_config.yaml
    :language: yaml


You can start and run your optimization like this:

..  code-block:: console

    $ python -m boa -c config.json
    Start time: 20221026T210522
    [INFO 10-26 21:05:22] ax.service.utils.instantiation: Inferred value type of ParameterType.FLOAT for parameter x0. If that is not the expected value type, you can explicity specify 'value_type' ('int', 'float', 'bool' or 'str') in parameter dict.
    [INFO 10-26 21:05:22] ax.service.utils.instantiation: Inferred value type of ParameterType.FLOAT for parameter x1. If that is not the expected value type, you can explicity specify 'value_type' ('int', 'float', 'bool' or 'str') in parameter dict.
    [INFO 10-26 21:05:22] ax.service.utils.instantiation: Created search space: SearchSpace(parameters=[RangeParameter(name='x0', parameter_type=FLOAT, range=[-5.0, 10.0]), RangeParameter(name='x1', parameter_type=FLOAT, range=[0.0, 15.0])], parameter_constraints=[]).
    [INFO 10-26 21:05:22] Scheduler: `Scheduler` requires experiment to have immutable search space and optimization config. Setting property immutable_search_space_and_opt_config to `True` on experiment.
    [INFO 10-26 21:05:22] Scheduler: Running trials [0]...
    [INFO 10-26 21:05:23] Scheduler: Running trials [1]...
    [INFO 10-26 21:05:24] Scheduler: Generated all trials that can be generated currently. Model requires more data to generate more trials.
    [INFO 10-26 21:05:24] Scheduler: Retrieved COMPLETED trials: 0 - 1.
    [INFO 10-26 21:05:24] Scheduler: Fetching data for trials: 0 - 1.
    [INFO 10-26 21:05:24] Scheduler: Running trials [2]...
    [INFO 10-26 21:05:25] Scheduler: Running trials [3]...
    [INFO 10-26 21:05:25] Scheduler: Running trials [4]...
    [INFO 10-26 21:05:26] Scheduler: Retrieved COMPLETED trials: 2 - 4.
    [INFO 10-26 21:05:26] Scheduler: Fetching data for trials: 2 - 4.

    Trials completed! Total run time: 3
    Saved JSON-serialized state of optimization to `/path/to/working/dir/boa_runs_20221026T210522/scheduler.json`.
