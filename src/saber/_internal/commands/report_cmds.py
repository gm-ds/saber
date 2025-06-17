#!/usr/bin/env python3

import json
from argparse import Namespace


def _html_report(parsed_args: Namespace, Results: dict, Config: dict) -> None:
    from saber._internal.output import Report

    report = Report(parsed_args.html_report, Results, Config)
    report.output_page()


def _md_report(parsed_args: Namespace, Results: dict, Config: dict) -> None:
    from saber._internal.output import Report

    report = Report(parsed_args.md_report, Results, Config)
    report.output_md()


def _table_html_report(parsed_args: Namespace, Results: dict, Config: dict) -> None:
    from saber._internal.output import Report

    summary = Report(parsed_args.table_html_report, Results, Config)
    summary.output_summary(True)


def _print_json(parsed_args: Namespace, Results: dict) -> None:
    if parsed_args.print_json:
        print(json.dumps(Results, indent=2, sort_keys=False))
