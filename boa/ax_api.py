# flake8: noqa
# from ax.modelbridge.torch import TorchModelBridge
import ax.utils as ax_utils
from ax.adapter import Adapter
from ax.adapter.registry import Generators as Models
from ax.adapter.torch import TorchAdapter as TorchModelBridge
from ax.api.client import (
    ChoiceParameterConfig,
    Client,
    DerivedParameterConfig,
    RangeParameterConfig,
)
from ax.api.protocols.metric import IMetric
from ax.api.protocols.runner import IRunner
from ax.api.types import TParameterization
from ax.api.utils.generation_strategy_dispatch import (
    choose_generation_strategy as choose_generation_strategy_new,
)
from ax.api.utils.structs import GenerationStrategyDispatchStruct
# Model configuration
from ax.generators.torch.botorch_modular.surrogate import ModelConfig
from ax.core import (
    BatchTrial,
    ChoiceParameter,
    Data,
    Experiment,
    FixedParameter,
    Metric,
    MultiObjective,
    MultiObjectiveOptimizationConfig,
    Objective,
    OptimizationConfig,
    OutcomeConstraint,
    RangeParameter,
    Runner,
    SearchSpace,
    Trial,
)
from ax.core.base_trial import BaseTrial
from ax.core.metric import MetricFetchE
from ax.core.objective import ScalarizedObjective
from ax.core.runner import Runner
from ax.core.trial_status import TrialStatus
from ax.exceptions.core import AxError
from ax.exceptions.storage import JSONDecodeError, JSONEncodeError
from ax.generation_strategy.center_generation_node import CenterGenerationNode

# from ax.modelbridge.dispatch_utils import choose_generation_strategy
from ax.generation_strategy.dispatch_utils import (
    choose_generation_strategy_legacy as choose_generation_strategy,
)
from ax.generation_strategy.generation_node import GenerationNode as GenerationStep

# from ax.modelbridge.generation_strategy import GenerationStrategy
from ax.generation_strategy.generation_strategy import GenerationStrategy
from ax.generators.torch.botorch_modular.surrogate import Surrogate, SurrogateSpec
from ax.metrics.noisy_function import NoisyFunctionMetric
from ax.orchestration.orchestrator import FailureRateExceededError, Orchestrator
from ax.orchestration.orchestrator_options import (
    OrchestratorOptions,
)
from ax.plot.contour import plot_contour_plotly
from ax.plot.helper import get_range_parameters_from_list
from ax.plot.pareto_frontier import plot_pareto_frontier
from ax.plot.pareto_utils import compute_posterior_pareto_frontier
from ax.plot.slice import interact_slice_plotly
from ax.plot.trace import optimization_trace_single_method_plotly

# *from ax.models.torch.botorch_moo import MultiObjectiveBotorchModel   ***************
from ax.service.utils.instantiation import InstantiationBase, TParameterRepresentation
from ax.service.utils.report_utils import exp_to_df
from ax.storage.botorch_modular_registry import (
    ACQUISITION_FUNCTION_REGISTRY,
    CLASS_TO_REGISTRY,
    CLASS_TO_REVERSE_REGISTRY,
)
from ax.storage.json_store.decoder import (
    generation_strategy_from_json,
    object_from_json,
)
from ax.storage.json_store.encoder import object_to_json
from ax.storage.json_store.registry import (
    CORE_CLASS_DECODER_REGISTRY,
    CORE_CLASS_ENCODER_REGISTRY,
    CORE_DECODER_REGISTRY,
    CORE_ENCODER_REGISTRY,
    botorch_modular_to_dict,
    class_from_json,
)
from ax.storage.metric_registry import CORE_METRIC_REGISTRY
from ax.storage.runner_registry import CORE_RUNNER_REGISTRY
from ax.utils.common.base import Base as AxBase
from ax.utils.common.docutils import copy_doc
from ax.utils.common.result import Err, Ok
from ax.utils.measurement.synthetic_functions import FromBotorch, branin, from_botorch
from ax.api.utils.instantiation.from_string import optimization_config_from_string
from botorch.optim import optimize_acqf
from botorch.models.map_saas import EnsembleMapSaasSingleTaskGP

Scheduler = Orchestrator
SchedulerOptions = OrchestratorOptions
