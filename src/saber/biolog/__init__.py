"""Biolog module for custom logging and testing functionality.

This module provides enhanced logging capabilities specifically designed for
this project. It includes:

- CustomLogger: A logger with contextual information injection
- ContextFilter: A logging filter for dynamic context injection
- LoggerLike: A protocol defining the standard logger interface

The module is designed to support tracking context across different Galaxy instances tests and compute endpoints.

GalaxyTest is A class for managing and executing workflow tests on Galaxy instances, while WFPathError and WFInvocation handle specific workflow path and invocation errors.

Classes:
    CustomLogger: Main logging class with file rotation and syslog support
    ContextFilter: Filter for injecting Galaxy/Pulsar context into log records
    LoggerLike: Protocol defining the standard logging interface
    GalaxyTest: Class for managing Galaxy workflow tests
    WFPathError: Exception for workflow path errors
    WFInvocation: Class for handling workflow invocations and results

Example:
    Basic usage of the CustomLogger:

    >>> from saber.biolog import CustomLogger
    >>> logger = CustomLogger("my_test")
    >>> logger.update_log_context("galaxy_main", "pulsar_endpoint_1")
    >>> logger.info("Starting pipeline n.1")

"""

from saber.biolog.logger import CustomLogger
from saber.biolog.bioblend_testjobs import GalaxyTest, WFPathError, WFInvocation
from saber.biolog.loglike import LoggerLike

__all__ = ["CustomLogger", "GalaxyTest", "WFPathError", "WFInvocation", "LoggerLike"]
