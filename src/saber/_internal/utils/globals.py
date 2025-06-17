#!/usr/bin/env python3

"""Global constants and configuration values for the saber application.

This module defines application-wide constants used throughout the saber
Galaxy workflow automation system. These include the tool name, parser
defaults, and a dictionary of exit codes for various error conditions.

Attributes:
    TOOL_NAME (str): The name of the saber application tool.
    P (str): Default placeholder value for parser operations.
    ERR_CODES (dict[str, int]): Mapping of error type names to their
        corresponding exit codes. Keys include:
            - "path": Path-related errors
            - "api": API-related errors
            - "args": Argument parsing errors
            - "jinja2": Jinja2 template errors
            - "tto": Timeout errors
            - "gal": Galaxy-specific errors
            - "job": Job execution errors

Note:
    Exit codes are used to provide specific error information to calling
    processes and scripts, enabling better error handling and debugging.
"""

# Secure Config
TOOL_NAME: str = "saber"

# Parser Defaults
P: str = "place_holder"

# Exit Codes
ERR_CODES: dict[str, int] = {
    "path": 1,
    "api": 3,
    "args": 2,
    "jinja2": 4,
    "tto": 42,
    "gal": 10,
    "job": 42,
}
