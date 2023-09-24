"""
Compatibility layer for filelock ( https://pypi.org/project/filelock/ );
commonly packaged by Linux distributions but might not be available
in some environments.
"""

import os
from typing import ContextManager

if os.getenv("PYTEST_XDIST_WORKER"):
    # running under pytest-xdist; filelock is required for reliability
    from filelock import FileLock
else:
    # normal test execution, no port races
    import contextlib
    from typing import Any

    def FileLock(*args: Any, **kwargs: Any) -> ContextManager[None]:
        return contextlib.nullcontext()
