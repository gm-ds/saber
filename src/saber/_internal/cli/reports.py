#!/usr/bin/env python3

from datetime import datetime

def _reports_helper(html: any, table: any, md: any, settings:dict) -> dict:    
    if html or table or md:
        start_dt = datetime.now()
        start_d = start_dt.strftime("%b %d, %Y %H:%M")
        string = settings.get("date_string", False)
        settings["date"] = {"sDATETIME": start_d, "nDATETIME": string}
        return settings
    else:
        return settings
    