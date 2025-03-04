# conftest.py
import logging
from io import StringIO
import pytest
import os
from open_mpic_core import TRACE_LEVEL


@pytest.fixture(autouse=True)
def clear_env_vars():
    """Clear environment variables before each test to prevent cross-test contamination."""
    # Store original environment
    original_env = dict(os.environ)

    # Clear all environment variables that might affect tests
    for key in list(os.environ.keys()):
        del os.environ[key]

    yield

    # Restore original environment after test
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def setup_logging():
    # Clear existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    log_output = StringIO()  # to be able to inspect what gets logged
    handler = logging.StreamHandler(log_output)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

    # Configure fresh logging
    logging.basicConfig(
        handlers=[handler],
        level=TRACE_LEVEL,
    )

    yield log_output
