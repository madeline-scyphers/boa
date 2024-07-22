Welcome to boa's documentation!
====================================

BOA is a high-level Bayesian optimization framework and model-wrapping toolkit. It is designed to be highly flexible and easy-to-use. BOA is built upon the lower-level packages `Ax <https://ax.dev>`_ (Adaptive Experimentation Platform, https://ax.dev//index.html) and `BoTorch <https://botorch.org>`_  to do the heavy lifting of the BO process and subsequent analysis. It supplements these lower-level packages with model-wrapping tools, language-agnostic features, and a flexible interface framework.


Key features
------------
- **Language-Agnostic**: Although BOA itself is written in Python, users do not need to write any Python code in order to use it. The user’s model, as well as the model wrapper, can be written in any programming language. Users can configure and run an optimization, save outputs, and view results entirely without writing any Python code. This allows the user to write their code in any language they want, or even reuse processing code they already have, and still have access to two of the most full-featured BO (BoTorch)  and GP (GPyTorch) libraries available today.
- **Scalability and Parallelization**: BOA handles optimization tasks of any size, from small problems to large, complex models. It supports parallel evaluations, allowing multiple optimization trials to run at the same time. This greatly reduces optimization time, especially when using powerful computing resources like supercomputing clusters. In many other BO packages, even if batched trial evaluation is supported, the actual parallelization implementation is left as an exercise to the user.
- **Reducing Boilerplate Code**: BOA aims to reduce the amount of boilerplate code often needed to set up and launch optimizations. BOA does this by providing an application programming interface (API) to the lower-level BO libraries BoTorch and Ax that it is built upon. This API is responsible for initializing, starting, and controlling the user’s optimization. The BOA API can be accessed and controlled almost entirely through a human readable, text based, YAML configuration file, reducing the need to write boilerplate setup code.
- **Automatic Saving and Resuming**: BOA automatically saves the state of an optimization process, allowing users to pause and resume optimizations easily. This ensures continuous progress and makes it easy to recover and retrieve results, even if there are interruptions or system crashes, making the workflow more resilient and user-friendly. Users can also add additional trials to a completed optimization or explore incoming results as the optimization is still running.
- **Support for Multi-Objective Optimization**: Streamlined and customizable support for multi-objective optimization.
- **Handling High-Dimensional and Complex Models**: Support for high-dimensional problems.
- **Customizability**: BOA allows customization of the optimization process as needed, including adding constraints, adjusting the kernel or acquisition function, or incorporating an early stopping criterion.

Head over to the :doc:`Bayesian Optimization overview page <user_guide/bo_overview>` to read about Bayesian Optimization and how it works.

Contents
--------
.. toctree::
    :maxdepth: 2

    user_guide/index
    examples/index
    troubleshooting
    changelog
    Code reference <code_reference>
    gallery
    contributing


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
