#!/usr/bin/env python3
"""
CLI package initialization for the Saber tool.

This package provides the command-line interface components for the Saber tool,
which is designed to test multiple useGalaxy instances and Pulsar Endpoints.
The package includes argument parsing, configuration management, and the main
CLI entry point.

Package Structure:
    - args.py: Command-line argument parser with comprehensive validation
    - helpers.py: Utility functions for configuration and report setup
    - main.py: Main CLI entry point and command dispatcher

Public API:
    The package exposes two main components for external use:
    - Parser: Command-line argument parser class
    - main: Main CLI application entry point function

Internal Components:
    Helper functions (_init_config, _reports_helper) are imported but not exposed
    in the public API, as they are intended for internal package use only.
"""

from saber._internal.cli.args import Parser

from saber._internal.cli.helpers import _init_config, _reports_helper

from saber._internal.cli.main import main

# Components available when importing this package
__all__ = [
    "Parser",  # Command-line argument parser class
    "main",  # Main CLI application entry point
]

# Helper functions _init_config and _reports_helper are imported for
# internal package use.
