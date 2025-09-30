#!/usr/bin/env python3
"""Main entry point for the Saber CLI application.

This module serves as the primary command dispatcher for the Saber tool, which tests
multiple useGalaxy instances and Pulsar Endpoints with the BioBlend Library. It handles command-line argument
parsing, logger initialization, and routing to appropriate handlers based on
the provided arguments.

The module follows a command pattern where different argument combinations trigger
different command handlers:
- Configuration file operations (encrypt, decrypt, edit)
- Example settings generation
- Main workflow execution (workflow launcher)
"""

from saber._internal.cli import Parser
from saber._internal.utils import mock_get_default_config_path
from saber._internal.utils.globals import TOOL_NAME, P
from saber.biolog import CustomLogger


def main() -> int:
    """Main entry point for the Saber CLI application.

    Initializes the command-line parser, sets up logging, and dispatches to the
    appropriate command handler based on the parsed arguments. This function
    serves as the central "executor" for all CLI operations.

    Returns:
        int: Exit code indicating the result of the operation:
             - 0: Successful execution
             - Non-zero: Error occurred during execution

    Command Flow:
        1. Parse command-line arguments using the Parser class
        2. Initialize logging with the specified or default log directory
        3. Route to appropriate command handler based on arguments:
           - example_settings: Generate and display example configuration
           - encrypt: Encrypt a YAML configuration file
           - decrypt: Decrypt an encrypted configuration file
           - edit: Edit an encrypted configuration file
           - default: Launch the main workflow execution

    Note:
        Commands are processed in order of precedence:
        1. example_settings (highest priority)
        2. encrypt
        3. decrypt
        4. edit
        5. main workflow (default action)

    """
    # Initialize command-line argument parser with placeholder and default config path
    args = Parser(P, mock_get_default_config_path()).arguments()

    # Set up logging with tool name and specified/default log directory
    logger = CustomLogger(TOOL_NAME, args.log_dir)
    logger.info("Starting...")

    # Command routing based on parsed arguments (in order of precedence)

    # Handle example settings generation (highest priority)
    if args.example_settings:
        # Import and execute example settings command
        from saber._internal.commands import example_settings

        return example_settings()

    # Handle file encryption operations
    if args.encrypt:
        # Import and execute encryption command
        from saber._internal.commands import encrypt

        return encrypt(
            logger,
            args,
        )

    # Handle file decryption operations
    elif args.decrypt:
        # Import and execute decryption command
        from saber._internal.commands import decrypt

        return decrypt(
            logger,
            args,
        )

    # Handle encrypted file editing operations
    elif args.edit:
        # Import and execute edit command
        from saber._internal.commands import edit

        return edit(
            logger,
            args,
        )
    # Default action: execute main workflow
    else:
        # Import and execute the main job launcher workflow
        from saber._internal.cli import launcher

        return launcher(args, logger)
