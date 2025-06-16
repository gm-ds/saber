#!/usr/bin/env python3

from argparse import Namespace
from datetime import datetime


def _reports_helper(__args: Namespace, settings: dict) -> dict:
    if __args.html_report or __args.table_html_report or __args.md_report:
        start_dt = datetime.now()
        start_d = start_dt.strftime("%b %d, %Y %H:%M")
        string = settings.get("date_string", False)
        settings["date"] = {"sDATETIME": start_d, "nDATETIME": string}
        return settings
    else:
        return settings
