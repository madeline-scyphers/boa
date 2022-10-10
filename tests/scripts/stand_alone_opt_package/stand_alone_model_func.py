from ax import Trial
from ax.utils.measurement.synthetic_functions import branin


def run_branin_from_trial(trial: Trial) -> float:
    x0, x1 = trial.arm.parameters.get("x0"), trial.arm.parameters.get("x1")
    result = branin(x0, x1)
    return result
