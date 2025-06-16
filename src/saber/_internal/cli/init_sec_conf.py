#!/usr/bin/env python3

import sys

from saber._internal.core import SecureConfig
from saber._internal.utils.globals import (PATH_EXIT,
                             TOOL_NAME,)

def _init_config(logger_class: any, password, config_path) -> dict:
    try:
        # Initialize secure configuration
        if config_path is None:
            secure_config_instance = SecureConfig(TOOL_NAME)
            secure_config_instance.initialize_encryption(password)
        else:
            secure_config_instance = SecureConfig(TOOL_NAME, config_path)
            secure_config_instance.initialize_encryption(password)
        
        _config = secure_config_instance.load_config()
        _config["config_path"] = str(secure_config_instance.get_config_path())
        return _config

    except (ValueError, PermissionError) as e:
        logger_class.error(f"An error occurred with configuration: {e}")
        return PATH_EXIT
