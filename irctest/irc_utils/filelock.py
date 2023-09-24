"""
Compatibility layer for filelock ( https://pypi.org/project/filelock/ );
commonly packaged by Linux distributions but might not be available
in some environments.
"""

try:
    from filelock import FileLock
except ImportError:
    import contextlib
    import warnings

    warnings.warn(
        "filelock package unavailable, concurrent runs may race",
        RuntimeWarning,
    )

    def FileLock(*args, **kwargs):
        return contextlib.nullcontext()
