#!/usr/bin/env python3

def _html_report(__args, _results, _config):
    if __args.html_report:
        from saber._internal.output import Report
        report = Report(__args.html_report, _results, _config)
        report.output_page()
