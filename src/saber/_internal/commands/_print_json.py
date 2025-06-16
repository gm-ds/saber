#!/usr/bin/env python3

import json

def _print_json(__args, _results):
    if __args.print_json:
        print(json.dumps(_results, indent=2, sort_keys=False))