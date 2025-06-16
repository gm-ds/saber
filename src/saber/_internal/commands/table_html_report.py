#!/usr/bin/env python3

from argparse import Namespace


def _table_html_report(__args: Namespace, _results: dict, _config: dict) -> None:
    if __args.table_html_report:
        from saber._internal.output import Report

        summary = Report(__args.table_html_report, _results, _config)
        summary.output_summary(True)
