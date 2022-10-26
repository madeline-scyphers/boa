"""
boa package
"""
try:
    from boa._version import version

    __version__ = version
except ImportError:
    # package not installed
    __version__ = "0.0.0"

from boa.ax_instantiation_utils import *  # noqa
from boa.instantiation_base import *  # noqa
from boa.metrics.modular_metric import *  # noqa
from boa.runner import *  # noqa
from boa.storage import *  # noqa
from boa.wrappers.wrapper import *  # noqa
from boa.wrappers.wrapper_utils import *  # noqa
