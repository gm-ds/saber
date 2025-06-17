#!/usr/bin/env python3

from typing import Protocol


class LoggerLike(Protocol):
    """Protocol defining the interface for logger-like objects.

    This protocol defines the standard logging interface that any logger
    implementation should provide to work with saber's classes. It includes the five standard logging
    levels: debug, info, warning, error, and critical.

    This protocol is used for type hints to ensure compatibility
    with any logger implementation that provides these methods.
    """

    def debug(self, msg, *args, **kwargs):
        """Log a debug message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments for the logging method.
        """
        ...

    def info(self, msg, *args, **kwargs):
        """Log an info message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments for the logging method.
        """
        ...

    def warning(self, msg, *args, **kwargs):
        """Log a warning message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments for the logging method.
        """
        ...

    def error(self, msg, *args, **kwargs):
        """Log an error message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments for the logging method.
        """
        ...

    def critical(self, msg, *args, **kwargs):
        """Log a critical message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments for the logging method.
        """
        ...
