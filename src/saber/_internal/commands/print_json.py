#!/usr/bin/env python3

import json
from argparse import Namespace


def _print_json(parsed_args: Namespace, Results: dict) -> None:
    if parsed_args.print_json:
        print(json.dumps(Results, indent=2, sort_keys=False))
