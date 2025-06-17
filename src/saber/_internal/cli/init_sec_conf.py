#!/usr/bin/env python3

from argparse import Namespace

from saber._internal.core import SecureConfig
from saber._internal.utils.globals import PATH_EXIT, TOOL_NAME
from saber.biolog import LoggerLike


def _init_config(Logger: LoggerLike, parsed_args: Namespace) -> dict | int:
    try:
        # Initialize secure configuration
        if parsed_args.settings is None:
            secure_config_instance = SecureConfig(TOOL_NAME)
            secure_config_instance.initialize_encryption(parsed_args.password)
        else:
            secure_config_instance = SecureConfig(TOOL_NAME, parsed_args.settings)
            secure_config_instance.initialize_encryption(parsed_args.password)

        _config = secure_config_instance.load_config()
        _config["config_path"] = str(secure_config_instance.get_config_path())
        return _config

    except (ValueError, PermissionError) as e:
        Logger.error(f"An error occurred with configuration: {e}")
        return PATH_EXIT
