import pandas as pd

from ax.core.metric import Metric
from ax.core.base_trial import BaseTrial
from ax.core.data import Data

from ax import Trial

class FetchMetric(Metric):

    def fetch_trial_data(self, trial: BaseTrial) -> Data:
        """Obtains data via fetching it from ` for a given trial."""
        if not isinstance(trial, Trial):
            raise ValueError("This metric only handles `Trial`.")

        data = self.properties["queue"].get_outcome_value_for_completed_job(
            job_id=trial.index
        )

        metric_name = self.properties.get("objective_name", "ssqr")

        df_dict = {
            "trial_index": trial.index,
            "metric_name": metric_name,
            "arm_name": trial.arm.name,
            "mean": data.get(metric_name),
            # Can be set to 0.0 if function is known to be noiseless
            # or to an actual value when SEM is known. Setting SEM to
            # `None` results in Ax assuming unknown noise and inferring
            # noise level from data.
            "sem": None,
        }
        return Data(df=pd.DataFrame.from_records([df_dict]))