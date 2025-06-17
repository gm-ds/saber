#!/usr/bin/env python3

from argparse import Namespace
from datetime import datetime


def _reports_helper(parsed_args: Namespace, Config: dict) -> dict:
    if (
        parsed_args.html_report
        or parsed_args.table_html_report
        or parsed_args.md_report
    ):
        start_dt = datetime.now()
        start_d = start_dt.strftime("%b %d, %Y %H:%M")
        string = Config.get("date_string", False)
        Config["date"] = {"sDATETIME": start_d, "nDATETIME": string}
        return Config
    else:
        return Config
