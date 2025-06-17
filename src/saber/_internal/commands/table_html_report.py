#!/usr/bin/env python3

from argparse import Namespace


def _table_html_report(parsed_args: Namespace, Results: dict, Config: dict) -> None:
    if parsed_args.table_html_report:
        from saber._internal.output import Report

        summary = Report(parsed_args.table_html_report, Results, Config)
        summary.output_summary(True)
