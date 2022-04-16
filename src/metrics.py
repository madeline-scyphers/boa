from __future__ import annotations

from functools import partial
from typing import Callable, Optional

import numpy as np
import pandas as pd
from ax import Data, Metric, Trial
from ax.core.base_trial import BaseTrial
from ax.core.data import Data
from ax.core.types import TParameterization
from ax.metrics.noisy_function import NoisyFunctionMetric
from ax.utils.common.typeutils import checked_cast
from sklearn.metrics import mean_squared_error

from utils import get_dictionary_from_callable, serialize_init_args
from wrapper import Wrapper
from wrapper_utils import (
    evaluate,
    get_trial_dir,
    make_trial_dir,
    mse,
    run_model,
    write_configs,
)

# from ax.utils.common.serialization import extract_init_args, serialize_init_args



class ModelMetric(Metric):
    def fetch_trial_data(self, trial: BaseTrial) -> Data:
        """Obtains data via fetching it from ` for a given trial."""
        if not isinstance(trial, Trial):
            raise ValueError("This metric only handles `Trial`.")

        data = self.properties["queue"].get_outcome_value_for_completed_job(job_id=trial.index)

        df_dict = {
            "trial_index": trial.index,
            "metric_name": self.name,
            "arm_name": trial.arm.name,
            "mean": data.get(self.name),
            # Can be set to 0.0 if function is known to be noiseless
            # or to an actual value when SEM is known. Setting SEM to
            # `None` results in Ax assuming unknown noise and inferring
            # noise level from data.
            "sem": None,
        }
        return Data(df=pd.DataFrame.from_records([df_dict]))


class ModularMetric(Metric):
    def __init__(
        self,
        metric_to_eval: Callable,
        param_names: list[str] = None,
        noise_sd: Optional[float] = 0.0,
        metric_func_kwargs: Optional[dict] = None,
        wrapper: Optional[Wrapper] = None,
        *args,
        **kwargs
    ):
        self.param_names = param_names if param_names is not None else []
        self.noise_sd = noise_sd
        self.metric_func_kwargs = metric_func_kwargs or {}
        self.metric_to_eval = partial(metric_to_eval, **self.metric_func_kwargs)
        self.wrapper = wrapper
        super().__init__(*args, **kwargs)

    @classmethod
    def is_available_while_running(cls) -> bool:
        return True

    def fetch_trial_data(self, trial: BaseTrial, *args, **kwargs):
        wrapper_kwargs = (
            self.wrapper.fetch_trial_data(trial=trial, *args, **kwargs) if self.wrapper else {}
        )
        wrapper_kwargs = wrapper_kwargs or {}
        safe_kwargs = {"trial": trial, **kwargs, **wrapper_kwargs}
        if isinstance(self.metric_to_eval, Metric):
            return self.metric_to_eval.fetch_trial_data(
                *args,
                **get_dictionary_from_callable(self.metric_to_eval.fetch_trial_data, safe_kwargs),
            )
        else:
            return self._fetch_trial_data_of_func(*args, **safe_kwargs)

    def _fetch_trial_data_of_func(self, trial: BaseTrial, noisy: bool = True, **kwargs) -> Data:
        noise_sd = self.noise_sd if noisy else 0.0
        arm_names = []
        mean = []
        for name, arm in trial.arms_by_name.items():
            arm_names.append(name)
            val = self._evaluate(params=arm.parameters, **kwargs)
            if noise_sd:
                val = val + noise_sd * np.random.randn()
            mean.append(val)
        # indicate unknown noise level in data
        if noise_sd is None:
            noise_sd = float("nan")
        df = pd.DataFrame(
            {
                "arm_name": arm_names,
                "metric_name": self.name,
                "mean": mean,
                "sem": noise_sd,
                "trial_index": trial.index,
            }
        )
        return Data(df=df)

    def _evaluate(self, params: TParameterization, **kwargs) -> float:
        kwargs["x"] = np.array([params[p] for p in self.param_names])
        return self.metric_to_eval(**get_dictionary_from_callable(self.metric_to_eval, kwargs))

    def clone(self) -> "Metric":
        """Create a copy of this Metric."""
        cls = type(self)
        return cls(
            # **get_dictionary_from_callables([Metric, cls.__init__], vars(self), match_private=True),  # TODO don't use vars?
            **serialize_init_args(
                self, parents=[Metric], match_private=True
            ),  # TODO don't use vars?
        )


class MSE(ModularMetric):
    def __init__(self, metric_to_eval=mean_squared_error, *args, **kwargs):
        super().__init__(metric_to_eval=metric_to_eval, *args, **kwargs)
