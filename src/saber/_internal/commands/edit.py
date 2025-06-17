#!/usr/bin/env python3
"""Edit command implementation for Saber tool."""

from argparse import Namespace

from saber._internal.core import SecureConfig
from saber._internal.utils.globals import ERR_CODES, TOOL_NAME
from saber.biolog import LoggerLike


def _edit(Logger: LoggerLike, parsed_args: Namespace) -> int:
    """Edit an encrypted configuration file in a secure manner.

    Args:
        Logger: Logger instance for command output
        parsed_args: Parsed command line arguments containing:
            - edit: Path to file to edit
            - password: Password for decryption/encryption

    Returns:
        int: Exit status (0 for success, Non-zero for failure)

    Raises:
        ValueError: If decryption/encryption fails
        PermissionError: If file access is not permitted
    """
    try:
        secure_config_instance = SecureConfig(TOOL_NAME, parsed_args.edit)
        secure_config_instance.initialize_encryption(parsed_args.password)
        secure_config_instance.edit_config()
        Logger.info(f"File edited: {parsed_args.edit}")
        return 0

    except (ValueError, PermissionError) as e:
        Logger.error(f"An error occurred with configuration: {e}")
        return ERR_CODES["path"]
