#!/usr/bin/env python3

from argparse import Namespace
from datetime import datetime


def _reports_helper(_args: Namespace, settings: dict) -> dict:    
    if _args.html_report or _args.table_html_report or _args.md_report:
        start_dt = datetime.now()
        start_d = start_dt.strftime("%b %d, %Y %H:%M")
        string = settings.get("date_string", False)
        settings["date"] = {"sDATETIME": start_d, "nDATETIME": string}
        return settings
    else:
        return settings
    