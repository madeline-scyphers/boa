################
Package Overview
################


There are two core components to using boa: a configuration file, and a model wrapper. Each are detailed below.

*****************************
Creating a configuration File
*****************************

Configuration is usually done through a configuration file in YAML or json format. The goal of :doc:`BOA </index>` is allow as much functionality of the bayesian optimization through the configuration as possible. Allowing users to worry mostly about their model itself instead of the optimization. In the configuration file you can do a single objective, multi objective, or scalarized objective optimization. You can specify different acquisition functions, or let them be selected for you, what parameters you are optimizing, parameter constraints, outcome constraints, and more.


.. toctree::
    :maxdepth: 0

    /api/boa.config

.. note::
    We are adding more and more functionality to the configuration directly, but if there are features not supported in the boa configuration file yet, but are support in the underlying Ax or BoTorch libraries, you can customize things further  with your lauch script. See below.


Objective functions
====================

When specifying your objective function to minimize or maximize, :doc:`BOA </index>` comes with a number of metrics you can use with your model output, such as MSE, :math:`R^2`, and others. For a list of current list of premade available of metrics, see See :mod:`.metrics.metrics`

************************************************************************
Creating a model wrapper (Language Agnostic or Python API)
************************************************************************

Using a model with :doc:`BOA </index>` requires writing a minimal wrapper to define the essential functions needed for
:doc:`BOA </index>` to interact with the model (i.e. reading and writing configurations for the model, running the
model, and retrieving outputs from the model). This can be written in any language (not just python),
and there is a standard interface to follow.


See the :mod:`instructions for creating a model wrapper <.boa.wrappers>` for details.
See the :doc:`examples of model wrappers <.boa.wrappers>` for examples.
See :doc:`tutorials </examples/index>`  for a number of examples of model wrappers in both Python and R.


************************************************************************
Choosing a Custom Kernel and Acquisition Function
************************************************************************

BOA tries to make it easy to use the default kernel and acquisition function, but if you need to specify a different kernel or acquisition function, you can do so in the configuration file.

See :doc:`details on how to specify kernel and acquisition function <customizing_gp_acq.>` for details.

****************************************************
Creating a Python launch script (Usually Not Needed)
****************************************************

Most of the time you won't need to write a launch script because BOA has an built-in launch script in
its :mod:`.controller` that is called when calling `boa`. But if you do need more control over your launch script than the default
provides, you can either subclass :class:`.Controller` or write your own launch script. Subclassing
:class:`.Controller` might be easier if you just need to modify :meth:`.Controller.run` or :meth:`.Controller.initialize_wrapper` or :meth:`.Controller.initialize_scheduler`
but can utilize the rest of the functions. If you need a lot of customization, writing your own script might be
easier. Some Custom scripts are included in the link below.


See :doc:`examples of custom launch scripts <run_script>` for details.

*********************************************
Starting From Command Line
*********************************************

If you are using :doc:`BOA's </index>` in built :mod:`.controller` for your launch script,
you can start your run easily from the command line.

With your conda environment for boa activated, run::

    boa --config-path path/to/your/config/file

or::

    boa -c path/to/your/config/file

:doc:`BOA's </index>` will save the its current state automatically to a `scheduler.json` file in your output experiment directory every 1-few trials (depending on parallelism settings). It will also save a optimization.csv at the end of your run with the trial information as well in the same directory as scheduler.json. The console will output the Output directory at the start and end of your runs to the console, it will also throughout the run, whenever it saves the `scheduler.json` file, output to the console the location where the file is being saved. You can resume a stopped run from a scheduler file::

    boa --scheduler-path path/to/your/scheduler.json

or::

    boa -sp path/to/your/scheduler.json


For a list of options and descriptions, type::

    boa --help

A fuller example using the command line interface can be found  :doc:`here </examples/example_py_run>`

.. toctree::
    :maxdepth: 2

    run_script
    /api/boa.wrappers

*********************************************
Plotting Utility Functions
*********************************************
:doc:`BOA's </index>` provides a light plotting module to help with exploratory data analysis (EDA)

.. toctree::
    :maxdepth: 2

    /api/boa.plot
    /api/boa.plotting
