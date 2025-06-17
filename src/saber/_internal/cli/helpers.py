#!/usr/bin/env python3
"""
CLI helper functions for the Saber tool.

This module provides utility functions to support command-line interface operations,
including configuration initialization and report generation setup. These functions
handle some of the integration between parsed command-line arguments and the core application
functionality.
"""

from argparse import Namespace
from datetime import datetime
from typing import Union

from saber._internal.core import SecureConfig
from saber._internal.utils.globals import PATH_EXIT, TOOL_NAME
from saber.biolog import LoggerLike


def _init_config(Logger: LoggerLike, parsed_args: Namespace) -> Union[dict, int]:
    """
    Initialize and load the secure configuration for the Saber tool.

    Creates a SecureConfig instance, initializes encryption with the provided password,
    and loads the configuration data. Handles both default configuration paths and
    custom configuration file paths specified via command-line arguments.

    Args:
        Logger (LoggerLike): Logger instance for error reporting and debugging.
        parsed_args (Namespace): Parsed command-line arguments containing configuration
                               settings and password information.

    Returns:
        Union[dict, int]: Configuration dictionary with loaded settings and config path
                         on success, or PATH_EXIT integer code on failure.

    Raises:
        ValueError: When configuration file format is invalid or encryption fails.
        PermissionError: When unable to access configuration file due to permissions.

    Note:
        - If parsed_args.settings is None, uses the default configuration path
        - Adds 'config_path' key to the returned configuration dictionary
        - All exceptions are caught and logged, returning PATH_EXIT for graceful handling

    Example:
        >>> config = _init_config(logger, args)
        >>> if isinstance(config, dict):
        ...     print(f"Config loaded from: {config['config_path']}")
    """
    try:
        # Initialize secure configuration with appropriate path
        if parsed_args.settings is None:
            # Use default configuration path
            secure_config_instance = SecureConfig(TOOL_NAME)
        else:
            # Use custom configuration path from command line
            secure_config_instance = SecureConfig(TOOL_NAME, parsed_args.settings)

        # Initialize encryption with provided password
        secure_config_instance.initialize_encryption(parsed_args.password)

        # Load configuration data
        _config = secure_config_instance.load_config()

        # Add configuration path to the loaded config for reference
        _config["config_path"] = str(secure_config_instance.get_config_path())

        return _config

    except (ValueError, PermissionError) as e:
        Logger.error(f"An error occurred with configuration: {e}")
        return PATH_EXIT


def _reports_helper(parsed_args: Namespace, Config: dict) -> dict:
    """
    Configure report generation settings based on command-line arguments.

    Checks if any report generation options are enabled and adds timestamp
    information to the configuration dictionary. This function prepares the
    configuration for report generation by adding date/time.

    Args:
        parsed_args (Namespace): Parsed command-line arguments containing report
                               generation flags (html_report, table_html_report, md_report).
        Config (dict): Configuration dictionary to be updated with report settings.

    Returns:
        dict: Updated configuration dictionary with date/time information added
              if report generation is enabled, or unchanged configuration if no
              reports are requested.

    Note:
        - Only modifies the configuration if at least one report type is requested
        - Adds a 'date' key with both formatted string and boolean flag
        - The 'sDATETIME' contains human-readable timestamp for report headers
        - The 'nDATETIME' preserves existing date_string setting from config
    """
    # Check if any report generation is requested
    report_requested = any(
        [parsed_args.html_report, parsed_args.table_html_report, parsed_args.md_report]
    )

    if report_requested:
        # Generate timestamp for report metadata
        start_datetime = datetime.now()
        formatted_datetime = start_datetime.strftime("%b %d, %Y %H:%M")

        # Preserve existing date_string setting from config
        date_string_setting = Config.get("date_string", False)

        # Add date information to configuration
        Config["date"] = {
            "sDATETIME": formatted_datetime,
            "nDATETIME": date_string_setting,
        }

        return Config
    else:
        # No reports requested, return configuration unchanged
        return Config


def _launcher(Parsed_Args: Namespace, Logger: LoggerLike) -> int:
    """
    Main workflow launcher that loads configuration, executes, and reports.

    This function serves as the primary coordinator for the Saber tool's main workflow.
    It handles configuration initialization, executes the core workflow, and generates
    various output reports based on command-line arguments.

    Args:
        Parsed_Args (Namespace): Parsed command-line arguments containing configuration
                               options, output preferences, and workflow parameters.
        Logger (LoggerLike): Logger instance for tracking execution progress and errors.

    Returns:
        int: Exit code indicating the result of the workflow execution:
             - 0: Successful execution
             - Non-zero: Error occurred during configuration, execution, or reporting

    Report Generation:
        The function conditionally generates multiple report formats:
        - HTML report: Detailed formatted report for web viewing
        - Markdown report: Text-based report for documentation
        - HTML table report: Summary table format for quick overview
        - JSON output: Machine-readable results for automation

    Error Handling:
        - Configuration errors return early with error code
        - Workflow execution errors are propagated through return codes
        - Report generation is attempted independently for each format

    Note:
        Reports are generated independently, so failure in one format doesn't
        prevent generation of other formats. The workflow results are expected
        to be a list where results[0] is the exit code and results[1] contains
        the data for report generation.
    """
    _config = _init_config(Logger, Parsed_Args)

    # Early return if configuration initialization failed
    if not isinstance(_config, dict):
        return _config

    # Configure report settings and add timestamp metadata
    _config = _reports_helper(Parsed_Args, _config)

    # Execute the main workflow
    from _internal.core import _wf_launcher

    results = _wf_launcher(_config, Logger)

    if isinstance(results, int):
        return results

    # Generate requested output reports
    if isinstance(results, list):
        # Extract workflow data for report generation (results[1])
        # results[0] contains the exit code, results[1] contains the data

        if Parsed_Args.html_report:
            from saber._internal.commands import _html_report

            _html_report(Parsed_Args, results[1], _config)

        if Parsed_Args.md_report:
            from saber._internal.commands import _md_report

            _md_report(Parsed_Args, results[1], _config)

        if Parsed_Args.table_html_report:
            from saber._internal.commands import _table_html_report

            _table_html_report(Parsed_Args, results[1], _config)

        if Parsed_Args.print_json:
            from saber._internal.commands import _print_json

            _print_json(Parsed_Args, results[1])

        return results[0]
