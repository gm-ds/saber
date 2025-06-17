#!/usr/bin/env python3

"""Report generation commands for Saber tool."""

import json
from argparse import Namespace


def _html_report(parsed_args: Namespace, Results: dict, Config: dict) -> None:
    """Generate an HTML report from Workflow results.

    Args:
        parsed_args: Parsed command line arguments containing output path
        Results: Dictionary of workflow results
        Config: Dictionary of configuration settings
    """
    from saber._internal.output import Report

    report = Report(parsed_args.html_report, Results, Config)
    report.output_page()


def _md_report(parsed_args: Namespace, Results: dict, Config: dict) -> None:
    """Generate an Markdown report from Workflow results.

    Args:
        parsed_args: Parsed command line arguments containing output path
        Results: Dictionary of workflow results
        Config: Dictionary of configuration settings
    """
    from saber._internal.output import Report

    report = Report(parsed_args.md_report, Results, Config)
    report.output_md()


def _table_html_report(parsed_args: Namespace, Results: dict, Config: dict) -> None:
    """Generate an HTML table summary from workflow results.

    Args:
        parsed_args: Parsed command line arguments containing output path
        Results: Dictionary of workflow results
        Config: Dictionary of configuration settings
    """
    from saber._internal.output import Report

    summary = Report(parsed_args.table_html_report, Results, Config)
    summary.output_summary(True)


def _print_json(parsed_args: Namespace, Results: dict) -> None:
    """Print results in JSON format to stdout.

    Args:
        parsed_args: Parsed command line arguments containing flag
        Results: Dictionary of results to print
    """
    if parsed_args.print_json:
        print(json.dumps(Results, indent=2, sort_keys=False))
