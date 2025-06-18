"""Utility package for saber internal operations.

This module provides access to global constants, exit codes, and mock functions
used throughout the saber application for Galaxy workflow testing automation.

Exports:
    Constants from globals module for application-wide configuration
    Mock functions for testing and development purposes
"""

from saber._internal.utils.globals import (
    ERR_CODES as ERR_CODES,
    TOOL_NAME as TOOL_NAME,
    P as P,
)
from saber._internal.utils.example_config import _example
from saber._internal.utils.mock_functions import _mock_get_default_config_path

example = _example
mock_get_default_config_path = _mock_get_default_config_path
