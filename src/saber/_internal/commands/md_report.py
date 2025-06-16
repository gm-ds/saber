#!/usr/bin/env python3

from argparse import Namespace


def _md_report(__args: Namespace, _results: dict, _config: dict) -> None:
    if __args.md_report:
        from saber._internal.output import Report

        report = Report(__args.md_report, _results, _config)
        report.output_md()
