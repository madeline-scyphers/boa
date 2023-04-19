# Bayesian Optimization for Anything
BOA is a high-level Bayesian optimization framework and model wrapping tool for providing an easy-to-use interface
between models and the python libraries [Ax](https://ax.dev) and [BoTorch](https://botorch.org)

## Key features

- **Model agnostic**

    - Can be used for models in any language (not just python)
    - Can be used for Wrappers in any language (You don't even need to write any python!) See `Script Wrapper` for details on how to do that.
    - Simple to implement for new models, with minimal coding required

- **Scalable**

  - Can be used for simple models or complex models that require a lot of computational resources
  - Scheduler to manage individual model runs
  - Supports parallelization

- **Modular & customizable**

  - Can take advantages of the many features of Ax/BoTorch
  - Customizable objective functions, multi-objective optimization, acquisition functions, etc
  - Choice of built-in evaluation metrics, but it’s also easy to implement custom metrics




## Install requirements

- see [installation guide](https://pyboa.readthedocs.io/en/latest/user_guide/getting_started.html#installation) 

|                       |                                                                                                                                                                 |
|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Docs                  | [![Documentation Status](https://readthedocs.org/projects/pyboa/badge/?version=latest)](https://pyboa.readthedocs.io/en/latest/?badge=latest)                   |
| DOI                   | [![DOI](https://zenodo.org/badge/480579470.svg)](https://zenodo.org/badge/latestdoi/480579470)                                                                  |
| Conda Install         | [![Conda Version](https://anaconda.org/conda-forge/boa-framework/badges/version.svg)](https://anaconda.org/conda-forge/boa-framework)                           |
| PyPI Install          | [![PyPI version](https://badge.fury.io/py/boa-framework.svg)](https://badge.fury.io/py/boa-framework)                                                           |
| Github Latest release | [![Github release](https://img.shields.io/github/release/madeline-scyphers/boa.svg?label=tag&colorB=11ccbb)](https://github.com/madeline-scyphers/boa/releases) |
| Github dev release    | [![Github tag](https://img.shields.io/github/v/tag/madeline-scyphers/boa.svg?label=tag&colorB=11ccbb)](https://github.com/madeline-scyphers/boa/tags)           |
| Build Status          | [![ci](https://github.com/madeline-scyphers/boa/actions/workflows/CI.yaml/badge.svg)](https://github.com/madeline-scyphers/boa/actions/workflows/CI.yaml)       |
| Coverage              | [![codecov](https://codecov.io/gh/madeline-scyphers/boa/branch/main/graph/badge.svg)](https://codecov.io/gh/madeline-scyphers/boa)                              |
