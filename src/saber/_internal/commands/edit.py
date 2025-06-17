#!/usr/bin/env python3
from argparse import Namespace

from saber._internal.core import SecureConfig
from saber._internal.utils.globals import PATH_EXIT, TOOL_NAME
from saber.biolog import LoggerLike


def _edit(Logger: LoggerLike, parsed_args: Namespace) -> int:
    try:
        secure_config_instance = SecureConfig(TOOL_NAME, parsed_args.edit)
        secure_config_instance.initialize_encryption(parsed_args.password)
        secure_config_instance.edit_config()
        return 0

    except (ValueError, PermissionError) as e:
        Logger.error(f"An error occurred with configuration: {e}")
        return PATH_EXIT
