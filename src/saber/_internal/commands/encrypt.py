#!/usr/bin/env python3

"""Encryption command implementation for Saber tool."""


from argparse import Namespace

from saber._internal.core import SecureConfig
from saber._internal.utils import ERR_CODES, TOOL_NAME
from saber.biolog import LoggerLike


def _encrypt(Logger: LoggerLike, parsed_args: Namespace) -> int:
    """Encrypt a configuration file for secure storage.

    Args:
        Logger: Logger instance for command output
        parsed_args: Parsed command line arguments containing:
            - encrypt: Path to file to encrypt
            - password: Password for encryption

    Returns:
        int: Exit status (0 for success, Non-zero for failure)

    Raises:
        ValueError: If encryption fails
        PermissionError: If file access is not permitted

    """
    try:
        secure_config_instance = SecureConfig(TOOL_NAME, parsed_args.encrypt)
        secure_config_instance.initialize_encryption(parsed_args.password)
        secure_config_instance.encrypt_existing_file()
        Logger.info(f"File encrypted: {parsed_args.encrypt}")
        return 0

    except (ValueError, PermissionError) as e:
        Logger.error(f"An error occurred with configuration: {e}")
        return ERR_CODES["path"]
