#!/usr/bin/env python3

"""Report generation commands for Saber tool."""

import json
from argparse import Namespace
from jinja2 import TemplateError

from saber.biolog import LoggerLike
from saber._internal.utils.globals import ERR_CODES


def _html_report(
    parsed_args: Namespace, Results: dict, Config: dict, Logger: LoggerLike
) -> int:
    """Generate an HTML report from Workflow results.

    Args:
        parsed_args: Parsed command line arguments containing output path
        Results: Dictionary of workflow results
        Config: Dictionary of configuration settings
        Logger: Logger instance for command output

    """
    from saber._internal.output import Report

    try:
        report = Report(parsed_args.html_report, Results, Config, Logger)
        report.output_page()
        return 0
    except TemplateError:
        return ERR_CODES["jinja2"]
    except Exception:
        return ERR_CODES["path"]


def _md_report(
    parsed_args: Namespace, Results: dict, Config: dict, Logger: LoggerLike
) -> int:
    """Generate an Markdown report from Workflow results.

    Args:
        parsed_args: Parsed command line arguments containing output path
        Results: Dictionary of workflow results
        Config: Dictionary of configuration settings
        Logger: Logger instance for command output

    """
    from saber._internal.output import Report

    try:
        report = Report(parsed_args.md_report, Results, Config, Logger)
        report.output_md()
        return 0
    except TemplateError:
        return ERR_CODES["jinja2"]
    except Exception:
        return ERR_CODES["path"]


def _table_html_report(
    parsed_args: Namespace, Results: dict, Config: dict, Logger: LoggerLike
) -> int:
    """Generate an HTML table summary from workflow results.

    Args:
        parsed_args: Parsed command line arguments containing output path
        Results: Dictionary of workflow results
        Config: Dictionary of configuration settings
        Logger: Logger instance for command output

    """
    from saber._internal.output import Report

    try:
        summary = Report(parsed_args.table_html_report, Results, Config, Logger)
        summary.output_summary(True)
        return 0
    except TemplateError:
        return ERR_CODES["jinja2"]
    except Exception:
        return ERR_CODES["path"]


def _print_json(parsed_args: Namespace, Results: dict) -> int:
    """Print results in JSON format to stdout.

    Args:
        parsed_args: Parsed command line arguments containing flag
        Results: Dictionary of results to print

    """
    if parsed_args.print_json:
        print(json.dumps(Results, indent=2, sort_keys=False))
        return 0
