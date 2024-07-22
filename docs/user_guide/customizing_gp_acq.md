# Customizing Your Gaussian Process and Acquisition Function

BOA is designed with flexibility of options for selecting the acquisition function and
kernel. BOA could be used by advanced BO users that want to control detailed aspects of the
optimization. However, for non-domain experts of BO, BOA defaults to common sensible
choices. BOA defers to BoTorch's defaults of a Matern 5/2 kernel, one of the most widely
used and flexible choices for BO and GPs (Frazier, 2018; Riche and Picheny, 2021; Jakeman,
2023). This is considered to be a flexible and broadly applicable kernel (Riche and Picheny,2021) and it is used as the default by many other BO and GP toolkits (Akiba et al., 2019;
Balandat et al., 2020; Brea, 2023; Nogueira, 2014; Jakeman, 2023). Similarly, BOA defaults
to Expected Improvement (EI) for single-objective functions and Expected Hypervolume
Improvement (EHVI) for multi-objective problems, which are well-regarded for their
performance across a broad range of applications (Balandat et al., 2020; Daulton et al., 2021;
Frazier, 2018). Users do have the option to explicitly control steps in the optimization process
in the ‘generation strategy’ section of the configuration, for example, to control the number of
Sobol trials, if SAASBO should be utilized, etc. As an advanced use case, users can also
explicitly set up different kernels and acquisition functions for different stages in the
optimization if they so choose. On this page, we will go over both ways to customize, as well as link to some examples of how to do so.

## General Control Options

The `generation_strategy` section of the configuration file is where you can control the optimization process. This includes the number of Sobol trials, the number of initial points, the number of iterations, and whether to use SAASBO. The `generation_strategy` section is shown below with common options:

```yaml
generation_strategy:
    # Specific number of initialization trials, 
    # Typically, initialization trials are generated quasi-randomly.
    num_initialization_trials: 50 
    # Integer, with which to override the default max parallelism setting for all 
    # steps in the generation strategy returned from this function. Each generation 
    # step has a ``max_parallelism`` value, which restricts how many trials can run
    # simultaneously during a given generation step.
    max_parallelism_override: 10
    # Whether to use SAAS prior for any GPEI generation steps.
    # See, BO overview page, high dimensionality section for more details.
    use_saasbo: true  
    random_seed: 42  # Fixed random seed for the Sobol generator.
```

## Utilizing Ax's Predefined Kernels and Acquisition Functions

Ax has a number of predefined kernels and acquisition function combos that can be used in the optimization process. Each of these sit inside a "step" inside the generation strategy, where your optimization is broken into a number of "steps" and each step can have its own kernel and acquisition function. For example, the first step is usually a Sobol step that does a quasi-random initialization of the optimization process. The second step could be a "GPEI" step (GPEI is the Ax model class name, and is the default used for single objective optimization) that uses the Matern 5/2 kernel and the batched noisy Expected Improvement acquisition function.

```yaml

generation_strategy:
    steps:
        - model: Sobol
          num_trials: 50
          # specify the maximum number of trials to run in parallel
          # 
          max_parallelism: 10
        - model: GPEI
          num_trials: -1  # -1 means the rest of the trials
          max_parallelism: 10
``` 

Ax does not have a good spot in their docs currently that lists all the available kernels and acquisition functions combo models, but you can find them listed on their [api docs here](https://ax.dev/api/modelbridge.html#ax.modelbridge.registry.Models) and you can see the source code for the models by clicking the source link on the api docs page. Some of the available models are:

- `GPEI`: Gaussian Process Expected Improvement, the default for single objective optimization, uses the Matern 5/2 kernel
- `GPKG`: Gaussian Process Knowledge Gradient, uses the Matern 5/2 kernel
- `SAASBO`: Sparse Axis-Aligned Subspace Bayesian Optimization, see [BO Overview High Dimensionality](bo_overview.md#high-dimensionality) for more details, uses the Matern 5/2 kernel and the batched noisy Expected Improvement acquisition function
- `Sobol`: Sobol initialization
- `MOO`: Gaussian Process Expected Hypervolume Improvement, uses the Matern 5/2 kernel

If you want to specify your kernel and acquisition function, you can do so by creating a custom model. The way to do that is with the `BOTORCH_MODULAR` model. This model allows you to specify the kernel and acquisition function you want to use. Here is an example of how to use the `BOTORCH_MODULAR` model:

```yaml
generation_strategy:
    steps:
        - model: SOBOL
          num_trials: 5
        - model: BOTORCH_MODULAR
          num_trials: -1  # No limitation on how many trials should be produced from this step
          model_kwargs:
              surrogate:
                  botorch_model_class: SingleTaskGP  # BoTorch model class name
                  covar_module_class: RBFKernel  # GPyTorch kernel class name
                  mll_class: LeaveOneOutPseudoLikelihood  # GPyTorch MarginalLogLikelihood class name
              botorch_acqf_class: qUpperConfidenceBound  # BoTorch acquisition function class name
              acquisition_options:
                  beta: 0.5
``` 

In the above example, the `BOTORCH_MODULAR` model is used to specify the `SingleTaskGP` model class, the `RBFKernel` kernel class, and the `qUpperConfidenceBound` acquisition function class. The `qUpperConfidenceBound` acquisition function is a batched version of UpperConfidenceBound. The `beta` parameter is a hyperparameter of the acquisition function that controls the trade-off between exploration and exploitation.

BoTorch model classes can be found in the [BoTorch model api documentation](https://botorch.org/docs/models) and the BoTorch acquisition functions can be found in the [BoTorch acquisition api documentation](https://botorch.org/api/acquisition.html).

GPyTorch kernel classes can be found in the [GPyTorch kernel api documentation](https://gpytorch.readthedocs.io/en/latest/kernels.html).

The GPyTorch MarginalLogLikelihood classes can be found in the [GPyTorch MarginalLogLikelihood api documentation](https://gpytorch.readthedocs.io/en/latest/marginal_log_likelihoods.html). But the only MLL class that for sure work currently are `ExactMarginalLogLikelihood` and `LeaveOneOutPseudoLikelihood`. Other MLL classes may work, but they have not been tested and are depended on some other implementation details in Ax.


```{caution}
The `BOTORCH_MODULAR` class is an area of Ax's code that is still under active development and a lot of components of it are very dependent on the current implementation of Ax, BoTorch, and GPyTorch, and therefore it is impossible to test every possible combination of kernel and acquisition function. Therefore, it is recommended to use when possible the predefined models that Ax provides.
```



## References

Akiba, T., Sano, S., Yanase, T., Ohta, T., Koyama, M., 2019. Optuna: A next-generation hyperparameter optimization framework, Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining. Association for Computing Machinery: Anchorage, AK, USA, pp. 2623–2631.

Balandat, M., Karrer, B., Jiang, D.R., Daulton, S., Letham, B., Gordon Wilson, A., Bakshy, E., 2020. BOTORCH: a framework for efficient Monte-Carlo Bayesian optimization, Proceedings of the 34th International Conference on Neural Information Processing Systems. Curran Associates Inc.: Vancouver, BC, Canada, pp. 21524–21538.

Brea, J., 2023. BayesianOptimization.jl. https://github.com/jbrea/BayesianOptimization.jl (accessed 17 July 2024)

Daulton, S., Balandat, M., Bakshy, E., 2021. Parallel Bayesian optimization of multiple noisy objectives with expected hypervolume improvement, 35th Conference on Neural Information Processing Systems.

Frazier, P.I., 2018. Bayesian Optimization, Recent Advances in Optimization and Modeling of Contemporary Problems, pp. 255-278.

Jakeman, J.D., 2023. PyApprox: A software package for sensitivity analysis, Bayesian inference, optimal experimental design, and multi-fidelity uncertainty quantification and surrogate modeling. Environmental Modelling & Software 170 105825.

Nogueira, F., 2014. Bayesian Optimization: Open source constrained global optimization tool for Python. https://github.com/bayesian-optimization/BayesianOptimization (accessed 17 July 2024)

Riche, R.L., Picheny, V., 2021. Revisiting Bayesian Optimization in the light of the COCO benchmark. Struct Multidisc Optim 64, 3063–3087. https://doi.org/10.1007/s00158-021-02977-1
