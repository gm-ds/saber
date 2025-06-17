#!/usr/bin/env python3

"""Decryption command implementation for Saber tool."""

from argparse import Namespace

from saber._internal.core import SecureConfig
from saber._internal.utils.globals import ERR_CODES, TOOL_NAME
from saber.biolog import LoggerLike


def _decrypt(Logger: LoggerLike, parsed_args: Namespace) -> int:
    """Decrypt a previously encrypted configuration file.

    Args:
        Logger: Logger instance for command output
        parsed_args: Parsed command line arguments containing:
            - decrypt: Path to file to decrypt
            - password: Password for decryption

    Returns:
        int: Exit status (0 for success, Non-zero for failure)

    Raises:
        ValueError: If decryption fails due to invalid password or file format
        PermissionError: If file access is not permitted

    """
    try:
        secure_config_instance = SecureConfig(TOOL_NAME, parsed_args.decrypt)
        secure_config_instance.initialize_encryption(parsed_args.password)
        secure_config_instance.decrypt_existing_file()
        Logger.info(f"File decrypted: {parsed_args.decrypt}")
        return 0

    except (ValueError, PermissionError) as e:
        Logger.error(f"An error occurred with configuration: {e}")
        return ERR_CODES["path"]
