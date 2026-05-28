from botorch.acquisition.analytic import PosteriorMean
from botorch.acquisition.monte_carlo import qUpperConfidenceBound
from botorch.models.gp_regression import SingleTaskGP
from botorch.models.map_saas import EnsembleMapSaasSingleTaskGP
from gpytorch.kernels import RBFKernel
from gpytorch.mlls.exact_marginal_log_likelihood import ExactMarginalLogLikelihood
from gpytorch.mlls.leave_one_out_pseudo_likelihood import LeaveOneOutPseudoLikelihood

from boa import (
    ScriptWrapper,
)
from boa.client import get_client


def test_gen_steps_from_config(gen_strat1_config, tmp_path):
    generation_strategy = gen_strat1_config.generation_strategy

    assert generation_strategy.struct.method == "fast"
    assert generation_strategy.struct.initialization_budget == 5
    assert generation_strategy.model_config is None
    assert generation_strategy.botorch_acqf_class is None

    wrapper = ScriptWrapper(config=gen_strat1_config, experiment_dir=tmp_path)
    client = get_client(config=gen_strat1_config, wrapper=wrapper, runner=object())
    assert list(client.generation_strategy.nodes_by_name) == ["CenterOfSearchSpace", "Sobol", "MBM"]


def test_auto_gen_use_saasbo(saasbo_config):
    generation_strategy = saasbo_config.generation_strategy

    assert generation_strategy.struct.method == "custom"
    assert generation_strategy.model_config.botorch_model_class is EnsembleMapSaasSingleTaskGP
    assert generation_strategy.model_config.mll_class is ExactMarginalLogLikelihood
    assert generation_strategy.model_config.name == "BONSAI"
    assert generation_strategy.botorch_acqf_class is PosteriorMean


def test_modular_botorch(gen_strat_modular_botorch_config, tmp_path):
    generation_strategy = gen_strat_modular_botorch_config.generation_strategy
    model_config = generation_strategy.model_config

    assert generation_strategy.struct.method == "custom"
    assert model_config.botorch_model_class is SingleTaskGP
    assert model_config.covar_module_class is RBFKernel
    assert model_config.mll_class is LeaveOneOutPseudoLikelihood
    assert model_config.name == "custom_single_task_gp"
    assert generation_strategy.botorch_acqf_class is qUpperConfidenceBound

    wrapper = ScriptWrapper(config=gen_strat_modular_botorch_config, experiment_dir=tmp_path)
    client = get_client(config=gen_strat_modular_botorch_config, wrapper=wrapper, runner=object())
    generator_spec = client.generation_strategy.nodes_by_name["MBM"].generator_specs[0]
    surrogate_model_config = generator_spec.generator_kwargs["surrogate_spec"].model_configs[0]

    assert generator_spec.generator_kwargs["botorch_acqf_class"] is qUpperConfidenceBound
    assert surrogate_model_config.botorch_model_class is SingleTaskGP
    assert surrogate_model_config.covar_module_class is RBFKernel
    assert surrogate_model_config.mll_class is LeaveOneOutPseudoLikelihood
