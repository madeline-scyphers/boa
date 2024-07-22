# Bayesian Optimization for Anything

BOA is a high-level Bayesian optimization framework and model-wrapping toolkit. It is designed to be highly flexible and easy-to-use. BOA is built upon the lower-level packages [Ax](https://ax.dev) (Adaptive Experimentation Platform) and [BoTorch](https://botorch.org)  to do the heavy lifting of the BO process and subsequent analysis. It supplements these lower-level packages with model-wrapping tools, language-agnostic features, and a flexible interface framework.


## Key features

- **Language-Agnostic**: Although BOA itself is written in Python, users do not need to write any Python code in order to use it. The user’s model, as well as the model wrapper, can be written in any programming language. Users can configure and run an optimization, save outputs, and view results entirely without writing any Python code. This allows the user to write their code in any language they want, or even reuse processing code they already have, and still have access to two of the most full-featured BO (BoTorch)  and GP (GPyTorch) libraries available today.
- **Scalability and Parallelization**: BOA handles optimization tasks of any size, from small problems to large, complex models. It supports parallel evaluations, allowing multiple optimization trials to run at the same time. This greatly reduces optimization time, especially when using powerful computing resources like supercomputing clusters. In many other BO packages, even if batched trial evaluation is supported, the actual parallelization implementation is left as an exercise to the user.
- **Reducing Boilerplate Code**: BOA aims to reduce the amount of boilerplate code often needed to set up and launch optimizations. BOA does this by providing an application programming interface (API) to the lower-level BO libraries BoTorch and Ax that it is built upon. This API is responsible for initializing, starting, and controlling the user’s optimization. The BOA API can be accessed and controlled almost entirely through a human readable, text based, YAML configuration file, reducing the need to write boilerplate setup code.
- **Automatic Saving and Resuming**: BOA automatically saves the state of an optimization process, allowing users to pause and resume optimizations easily. This ensures continuous progress and makes it easy to recover and retrieve results, even if there are interruptions or system crashes, making the workflow more resilient and user-friendly. Users can also add additional trials to a completed optimization or explore incoming results as the optimization is still running.
- **Support for Multi-Objective Optimization**: Streamlined and customizable support for multi-objective optimization.
- **Handling High-Dimensional and Complex Models**: Support for high-dimensional problems.
- **Customizability**: BOA allows customization of the optimization process as needed, including adding constraints, adjusting the kernel or acquisition function, or incorporating an early stopping criterion.


## Next Steps

Head over to [installation guide](https://boa-framework.readthedocs.io/en/latest/user_guide/getting_started.html#installation) to get started with installing BOA. 

Or

Head over to [Bayesian Optimization Guide](https://boa-framework.readthedocs.io/en/stable/user_guide/bo_overview.html) to read about Bayesian Optimization and how it works.


|                       |                                                                                                                                                                 |
|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Docs                  | [![Documentation Status](https://readthedocs.org/projects/boa-framework/badge/?version=latest)](https://boa-framework.readthedocs.io/en/latest/?badge=latest)   |
| DOI                   | [![DOI](https://zenodo.org/badge/480579470.svg)](https://zenodo.org/badge/latestdoi/480579470)                                                                  |
| Conda Install         | [![Conda Version](https://anaconda.org/conda-forge/boa-framework/badges/version.svg)](https://anaconda.org/conda-forge/boa-framework)                           |
| PyPI Install          | [![PyPI version](https://badge.fury.io/py/boa-framework.svg)](https://badge.fury.io/py/boa-framework)                                                           |
| Github Latest release | [![Github release](https://img.shields.io/github/release/madeline-scyphers/boa.svg?label=tag&colorB=11ccbb)](https://github.com/madeline-scyphers/boa/releases) |
| Github dev release    | [![Github tag](https://img.shields.io/github/v/tag/madeline-scyphers/boa.svg?label=tag&colorB=11ccbb)](https://github.com/madeline-scyphers/boa/tags)           |
| Build Status          | [![ci](https://github.com/madeline-scyphers/boa/actions/workflows/CI.yaml/badge.svg)](https://github.com/madeline-scyphers/boa/actions/workflows/CI.yaml)       |
| Coverage              | [![codecov](https://codecov.io/gh/madeline-scyphers/boa/branch/main/graph/badge.svg)](https://codecov.io/gh/madeline-scyphers/boa)                              |
