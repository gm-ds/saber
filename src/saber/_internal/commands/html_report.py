#!/usr/bin/env python3

from argparse import Namespace


def _html_report(__args: Namespace, _results: dict, _config: dict) -> None:
    if __args.html_report:
        from saber._internal.output import Report

        report = Report(__args.html_report, _results, _config)
        report.output_page()
