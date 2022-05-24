Welcome to optiwrap's documentation!
====================================

``Optiwrap`` is a high-level Bayesian optimization framework and model wrapping tool. It provides an easy-to-use interface
between models and the python libraries ``Ax`` and ``BoTorch``.

Key features
------------
- **Model agnostic**

  - Can be used for models in any language (not just python)
  - Simple to implement for new models, with minimal coding required

- **Scalable**

  - Can be used for simple models or complex models that require a lot of computational resources
  - Scheduler to manage individual model runs
  - Supports parallelization

- **Modular & customizable**

  - Can take advantages of the many features of Ax/BoTorch
  - Customizable objective functions, multi-objective optimization, acquisition functions, etc
  - Choice of built-in evaluation metrics, but it’s also easy to implement custom metrics


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   getting_started
   user_guide/index
   Code reference <code_reference>


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
