#!/usr/bin/env python3
from argparse import Namespace

from saber._internal.core import SecureConfig
from saber._internal.utils import PATH_EXIT, TOOL_NAME
from saber.biolog import LoggerLike


def _encrypt(_logger: LoggerLike, _args: Namespace) -> int:
    try:
        secure_config_instance = SecureConfig(TOOL_NAME, _args.encrypt)
        secure_config_instance.initialize_encryption(_args.password)
        secure_config_instance.encrypt_existing_file()
        _logger.info(f"File encrypted: {_args.encrypt}")
        return 0

    except (ValueError, PermissionError) as e:
        _logger.error(f"An error occurred with configuration: {e}")
        return PATH_EXIT
