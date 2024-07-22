# Customizing Your Gaussian Process and Acquisition Function

BOA is designed with flexibility of options for selecting the acquisition function and
kernel. BOA could be used by advanced BO users that want to control detailed aspects of the
optimization. However, for non-domain experts of BO, BOA defaults to common sensible
choices. BOA defers to BoTorch&#39;s defaults of a Matern 5/2 kernel, one of the most widely
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




## References

Akiba, T., Sano, S., Yanase, T., Ohta, T., Koyama, M., 2019. Optuna: A next-generation hyperparameter optimization framework, Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining. Association for Computing Machinery: Anchorage, AK, USA, pp. 2623–2631.

Balandat, M., Karrer, B., Jiang, D.R., Daulton, S., Letham, B., Gordon Wilson, A., Bakshy, E., 2020. BOTORCH: a framework for efficient Monte-Carlo Bayesian optimization, Proceedings of the 34th International Conference on Neural Information Processing Systems. Curran Associates Inc.: Vancouver, BC, Canada, pp. 21524–21538.

Brea, J., 2023. BayesianOptimization.jl. https://github.com/jbrea/BayesianOptimization.jl (accessed 17 July 2024)

Daulton, S., Balandat, M., Bakshy, E., 2021. Parallel Bayesian optimization of multiple noisy objectives with expected hypervolume improvement, 35th Conference on Neural Information Processing Systems.

Frazier, P.I., 2018. Bayesian Optimization, Recent Advances in Optimization and Modeling of Contemporary Problems, pp. 255-278.

Jakeman, J.D., 2023. PyApprox: A software package for sensitivity analysis, Bayesian inference, optimal experimental design, and multi-fidelity uncertainty quantification and surrogate modeling. Environmental Modelling & Software 170 105825.

Nogueira, F., 2014. Bayesian Optimization: Open source constrained global optimization tool for Python. https://github.com/bayesian-optimization/BayesianOptimization (accessed 17 July 2024)

Riche, R.L., Picheny, V., 2021. Revisiting Bayesian Optimization in the light of the COCO benchmark. Struct Multidisc Optim 64, 3063–3087. https://doi.org/10.1007/s00158-021-02977-1
