#!/usr/bin/env python3

"""Global constants and configuration values for the saber application.

This module defines application-wide constants including the tool name,
parser defaults, and various exit codes used throughout the saber Galaxy
workflow automation system.

Constants:
    TOOL_NAME (str): The name of the application tool
    P (str): Default placeholder value for parser operations
    PATH_EXIT (int): Exit code for path-related errors
    API_EXIT (int): Exit code for API-related errors
    TIMEOUT_EXIT (int): Exit code for timeout errors
    GAL_ERROR (int): Exit code for Galaxy-specific errors
    JOB_ERR_EXIT (int): Exit code for job execution errors

Note:
    Exit codes are used to provide specific error information to calling
    processes and scripts, enabling better error handling and debugging.
"""

# Secure Config
TOOL_NAME = "saber"

# Parser Defaults
P = "place_holder"

# Exit Codes

PATH_EXIT = int(1)

API_EXIT = int(3)

TIMEOUT_EXIT = int(42)

GAL_ERROR = int(10)

JOB_ERR_EXIT = TIMEOUT_EXIT
