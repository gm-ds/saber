#!/usr/bin/env python3

def _md_report(__args, _results, _config):
    if __args.md_report:
        from saber._internal.output import Report
        report = Report(__args.md_report, _results, _config)
        report.output_md()