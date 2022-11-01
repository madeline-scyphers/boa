################
Package Overview
################


There are 2 core components to running boa, configuration, a model wrapper. Each are detailed below.

*****************************
Creating a configuration File
*****************************

Configuration is usually done through a configuration file in YAML or json format. The goal of :doc:`BOA </index>` is allow as much functionality of the bayesian optimization through the configuration as possible. Allowing users to worry mostly about their model itself instead of the optimization. In the configuration file you can do a single objective, multi objective, or scalarized objective optimization. You can specify different acquisition functions, or let them be selected for you, what parameters you are optimizing, parameter constraints, outcome constraints, and more.

See the :doc:`instructions for configurations files<configuration>` for details.

.. note::
    We are adding more and more functionality to the configuration directly, but if there are features not supported in the boa configuration file yet, but are support in the underlying Ax or BoTorch libraries, you can customize things further  with your run script. See below.


Objective functions
====================

When specifying your objective function to minimize or maximize, :doc:`BOA </index>` comes with a number of metrics you can use with your model output, such as MSE, :math:`R^2`, and others. For a list of current list of premade available of metrics, see See :mod:`.metrics.metrics`



************************
Creating a model wrapper
************************

Using a model with :doc:`BOA </index>` requires writing a minimal wrapper to define the essential functions needed for :doc:`BOA </index>` to interact
with the model (i.e. reading and writing configurations for the model, running the model, and retrieving outputs from
the model). This can be written in another language, and then there is a standard interface to follow


See the :mod:`instructions for creating a model wrapper <.boa.wrappers>` for details.

*********************************************
Creating a run script (Sometimes Needed)
*********************************************

Most of the time you won't need to write a run script because BOA has an built-in run script in its :mod:`.controller`. But if you do need more control over your run script than that, you can either subclass :class:`.Controller` or write your own run script. Subclassing :class:`.Controller` might be easier if you just need to modify :meth:`.Controller.run` or :meth:`.Controller.setup` but can utilize the rest of the functions. If you need a lot of customization, writing your own run script might be easier. Some Custom run scripts are included in the link below.


See :doc:`examples of custom run scripts <run_script>` for details.

*********************************************
Starting From Command Line
*********************************************

If you are using :doc:`BOA's </index>` in built :mod:`.controller` for your run script, you can start your run easily from the command line

With your conda environment activated:

    python -m boa --config_path path/to/your/config/file

type:

    python -m boa --help

for a list of options and descriptions

.. todo::
    Add more information here when other language feature is fully merged in

A fuller example using the command line interface can be found  :doc:`here </examples/example_py_run>`

.. toctree::
    :maxdepth: 2

    configuration
    run_script
    /api/boa.wrappers
