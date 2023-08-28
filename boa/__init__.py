"""
boa package
"""
try:
    from boa.__version__ import __version__

except ImportError:
    # package not installed
    __version__ = "0.0.0"

from boa.ax_instantiation_utils import *  # noqa
from boa.config import *  # noqa
from boa.controller import *  # noqa
from boa.instantiation_base import *  # noqa
from boa.metrics.metric_funcs import *  # noqa
from boa.metrics.metrics import *  # noqa
from boa.metrics.modular_metric import *  # noqa
from boa.metrics.synthetic_funcs import *  # noqa
from boa.plotting import (  # noqa
    app_view,
    plot_contours,
    plot_metrics_trace,
    plot_pareto_frontier,
    plot_slice,
    scheduler_to_df,
)
from boa.registry import _add_common_encodes_and_decodes
from boa.runner import *  # noqa
from boa.scheduler import *  # noqa
from boa.storage import *  # noqa
from boa.template import render_template_from_path  # noqa
from boa.wrappers.base_wrapper import *  # noqa
from boa.wrappers.script_wrapper import *  # noqa
from boa.wrappers.wrapper_utils import *  # noqa

_add_common_encodes_and_decodes()

del _add_common_encodes_and_decodes


# warnings from non boa modules to suppress
# we only suppress very specific files, not entire libraries
# so we don't accidentally suppress more than we need

import warnings  # noqa

# In AX, this error happens which we can't control
# In a future version of pandas,
# a length 1 tuple will be returned when iterating over a groupby with a grouper equal to a list of length 1.
warnings.filterwarnings("ignore", category=FutureWarning, module="ax.core.observation")
# In AX, this error happens, referring to their own calling of their own function
warnings.filterwarnings(
    "ignore", message="You passed `transform_outcomes_and_configs=False`.*", module="ax.modelbridge.modelbridge_utils"
)

del warnings
