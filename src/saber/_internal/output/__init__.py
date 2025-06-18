"""Saber CLI code to generate reports files.

The module makes available templates and the Report class for
report generation in different formats like HTML and Markdown.

"""

from saber._internal.output.reports import _Report

Report = _Report
