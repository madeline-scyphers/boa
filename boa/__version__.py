try:
    from boa._version import version

    __version__ = version
except ImportError:
    # package not installed
    __version__ = "0.0.0"
