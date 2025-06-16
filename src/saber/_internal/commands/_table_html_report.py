#!/usr/bin/env python3

def _table_html_report(__args, _results, _config):
    if __args.table_html_report:
        from saber._internal.output import Report
        summary = Report(__args.table_html_report, _results, _config)
        summary.output_summary(True)