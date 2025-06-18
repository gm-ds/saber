#!/usr/bin/env python3

"""Example settings command implementation for Saber tool."""

from saber._internal.utils import example


def _example_settings() -> int:
    """Display example configuration settings.

    Returns:
        int: Always returns 0 (success)

    """
    print(example)
    return 0
