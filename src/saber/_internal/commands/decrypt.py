#!/usr/bin/env python3

from argparse import Namespace

from saber._internal.core import SecureConfig
from saber._internal.utils.globals import PATH_EXIT, TOOL_NAME


def _decrypt(logger_inst: any, _args: Namespace) -> int:
    try:
        secure_config_instance = SecureConfig(TOOL_NAME, _args.decrypt)
        secure_config_instance.initialize_encryption(_args.password)
        secure_config_instance.decrypt_existing_file()
        logger_inst.info(f"File decrypted: {_args.decrypt}")
        return 0

    except (ValueError, PermissionError) as e:
        logger_inst.error(f"An error occurred with configuration: {e}")
        return PATH_EXIT