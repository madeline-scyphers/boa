.. _wrapper-user-guide:

########################
Creating a model wrapper
########################

To create a model wrapper, you will create a child class of boa's :class:`~boa.wrapper.BaseWrapper`
class. :class:`~boa.wrapper.BaseWrapper` defines the core functions that must be defined in your model
wrapper:

* :meth:`~boa.wrapper.BaseWrapper.load_config`: Defines how to load the configuration file for the experiment. There is
  a default version of this function that can be used.
* :meth:`~boa.wrapper.BaseWrapper.write_configs`: Defines how to write configurations for the model. This is needed so
  that ``boa`` can pass the parameters it generates in each trial to the model.
* :meth:`~boa.wrapper.BaseWrapper.run_model`: Defines how to run the model.
* :meth:`~boa.wrapper.BaseWrapper.set_trial_status`: Defines how to determine the status of a trial (i.e., if the model
  run is completed, still running, failed, etc).
* :meth:`~boa.wrapper.BaseWrapper.fetch_trial_data`: Retrieves the trial data and prepares it for the metric(s) used in
  the objective function.

Apart from these core functions, your model wrapper can have additional functions as needed (for example, to help with
formatting or scaling model outputs,  )

See :doc:`FETCH3 <fetch3:user_guide/optimization>`'s :mod:`Wrapper <fetch3:fetch3.optimize.fetch_wrapper>` for an
example.


*************************
Example wrapper functions
*************************

The ``write_configs`` function
==============================

FETCH3's wrapper provides a simple example of this function for the case where the parameters simply need to be written
to a yaml file:

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: write_configs


The ``run_model`` function
==========================

This function can simply launch a python or shell script to start a model run. FETCH3's wrapper provides an example of
this function for the case where the model run is started by running a python script with command line arguments:

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: Fetch3Wrapper.run_model


The ``set_trial_status`` function
=================================

In this example, the trial status is determined by checking the log file of the model for specific outputs:

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: Fetch3Wrapper.set_trial_status


The ``fetch_trial_data`` function
=================================

.. rli:: https://raw.githubusercontent.com/jemissik/fetch3_nhl/develop/fetch3/optimize/fetch_wrapper.py
   :pyobject: Fetch3Wrapper.fetch_trial_data