#!/usr/bin/env python3

from argparse import Namespace

from saber._internal.core import SecureConfig
from saber._internal.utils.globals import PATH_EXIT, TOOL_NAME
from saber.biolog import LoggerLike


def _decrypt(Logger: LoggerLike, parsed_args: Namespace) -> int:
    try:
        secure_config_instance = SecureConfig(TOOL_NAME, parsed_args.decrypt)
        secure_config_instance.initialize_encryption(parsed_args.password)
        secure_config_instance.decrypt_existing_file()
        Logger.info(f"File decrypted: {parsed_args.decrypt}")
        return 0

    except (ValueError, PermissionError) as e:
        Logger.error(f"An error occurred with configuration: {e}")
        return PATH_EXIT
