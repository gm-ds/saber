#!/usr/bin/env python3

from saber._internal.cli import Parser
from saber._internal.utils import TOOL_NAME, P, mock_get_default_config_path
from saber.bbl import CustomLogger

def _main():

    args = Parser(P, mock_get_default_config_path()).arguments()
    logger = CustomLogger(TOOL_NAME, args.log_dir)
    logger.info("Starting...")

    if args.example_settings:
        from saber._internal.commands import _example_settings
        return _example_settings()

    if args.encrypt:
        from saber._internal.commands import _encrypt
        return _encrypt(logger,
                args,
                )
    
    elif args.decrypt:
        from saber._internal.commands import _decrypt
        return _decrypt(logger,
                args,
                )
        
    elif args.edit:
        from saber._internal.commands import _edit
        return _edit(logger,
                args,
                )
    else:
        from saber._internal.core.main import _job_launcher
        return _job_launcher(args, logger)
