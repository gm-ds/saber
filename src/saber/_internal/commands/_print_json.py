#!/usr/bin/env python3

import json
from argparse import Namespace

def _print_json(__args: Namespace, _results: dict) -> None:
    if __args.print_json:
        print(json.dumps(_results, indent=2, sort_keys=False))