#!/usr/bin/env python3

from argparse import Namespace


def _html_report(parsed_args: Namespace, Results: dict, Config: dict) -> None:
    if parsed_args.html_report:
        from saber._internal.output import Report

        report = Report(parsed_args.html_report, Results, Config)
        report.output_page()
