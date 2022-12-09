"""
boa package
"""
try:
    from boa._version import version

    __version__ = version
except ImportError:
    # package not installed
    __version__ = "0.0.0"

from boa.__main__ import run  # noqa
from boa.ax_instantiation_utils import *  # noqa
from boa.controller import *  # noqa
from boa.instantiation_base import *  # noqa
from boa.metrics.metric_funcs import *  # noqa
from boa.metrics.metrics import *  # noqa
from boa.metrics.modular_metric import *  # noqa
from boa.metrics.synthetic_funcs import *  # noqa
from boa.registry import _add_common_encodes_and_decodes
from boa.runner import *  # noqa
from boa.scheduler import *  # noqa
from boa.storage import *  # noqa
from boa.wrappers.base_wrapper import *  # noqa
from boa.wrappers.script_wrapper import *  # noqa
from boa.wrappers.wrapper_utils import *  # noqa

_add_common_encodes_and_decodes()

del _add_common_encodes_and_decodes
