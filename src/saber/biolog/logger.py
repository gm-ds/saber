#!/usr/bin/env python3

import logging
import os
import platform
from pathlib import Path

from platformdirs import user_log_dir


# Filters, from logging docs:
class ContextFilter(logging.Filter):
    """A filter that injects contextual dynamic information into log records.

    This filter adds Galaxy instance and Pulsar endpoint information to each
    log record, allowing for better tracking of log messages across different
    contexts during test execution.

    Attributes:
        context (dict): Dictionary containing contextual information to inject
            into log records.

    """

    def __init__(self, context: dict) -> None:
        """Initialize the ContextFilter with a context dictionary.

        Args:
            context (dict): Dictionary containing contextual information.
                Expected keys are 'GalaxyInstance' and 'Endpoint'.

        """
        super().__init__()  # Initialize the parent class!
        self.context = context

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter and modify log records by adding contextual information.

        This method is called for each log record and adds galaxy and pulsar
        attributes to the record based on the current context.

        Args:
            record (logging.LogRecord): The log record to be filtered.

        Returns:
            bool: Always returns True to allow all records to pass through.

        """
        record.galaxy = self.context.get("GalaxyInstance", "None")
        record.pulsar = self.context.get("Endpoint", "Default")
        return True


class CustomLogger:
    """A custom logger implementation with contextual information and file rotation.

    This logger provides enhanced logging capabilities including:
    - Contextual information injection (Galaxy instance and endpoint)
    - File rotation (daily rotation with 7-day backup retention)
    - Syslog integration
    - BioBlend logger integration
    - Platform-specific log directory handling

    Attributes:
        _log_context (dict): Current logging context containing Galaxy instance
            and endpoint information.
        _log_name (str): Name of the logger instance.
        _logger (logging.Logger): The underlying Python logger instance.

    """

    def __init__(self, init_log_name: str, dir: Path = None) -> None:
        """Initialize the CustomLogger with specified name and optional directory.

        Args:
            init_log_name (str): The name to assign to this logger instance.
            dir (Path, optional): Custom directory path for log files. If None,
                uses platform-specific default directories. Defaults to None.

        """
        self._log_context = {"GalaxyInstance": "None", "Endpoint": "None"}
        self._log_name = init_log_name

        # Initialize actual logger
        self._logger = None
        self._setup_logging(dir)

    def _setup_logging(self, log_dir: Path = None) -> None:
        """Set up logging with custom formatter, handlers, and syslog.

        Configures the logger with:
        - Timed rotating file handler (daily rotation, 7-day retention)
        - Custom formatter with contextual information
        - Syslog handler for system-level logging
        - BioBlend logger integration

        Log file locations:
        - Root user: /var/log/saber/
        - Regular user: Platform-specific user log directory
        - Custom: Provided log_dir parameter

        Args:
            log_dir (Path, optional): Custom directory for log files. If provided,
                the directory will be created if it doesn't exist. Defaults to None.

        """
        log_name = f"{self._log_name}.log"
        try:
            if log_dir is not None:
                log_dir = (
                    (log_dir.parent / log_dir.stem) if log_dir.suffix != "" else log_dir
                )
                os.makedirs(log_dir, exist_ok=True)
                log_file = str(log_dir) + "/" + log_name
            elif os.geteuid() == 0:
                log_dir = "/var/log/saber"
                os.makedirs(log_dir, exist_ok=True)
                log_file = f"/var/log/saber/{log_name}"
            else:
                log_dir = user_log_dir("saber")
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, f"{log_name}")
        except Exception as e:
            print(f"Couldn't setup log file: {e}")

        # Setting up handler for rotating logs and custom format
        handler = logging.handlers.TimedRotatingFileHandler(
            log_file, when="midnight", backupCount=7
        )
        formatter = logging.Formatter(
            "%(asctime)s %(name)s: %(levelname)-8s [%(galaxy)s@%(pulsar)s] %(message)s",
            "%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)

        # Set logger instancelog_context
        self._logger = logging.getLogger(self._log_name)
        self._logger.setLevel(logging.INFO)

        # Avoid duplicate handlers
        self._logger.handlers.clear()
        self._logger.addHandler(handler)

        # Setup context filter
        self._logger.filters.clear()
        self._logger.addFilter(ContextFilter(self._log_context))

        self._setup_syslog()

        # Attach BioBlend logger to use the same handlers and filter
        bioblend_logger = logging.getLogger("bioblend")
        bioblend_logger.setLevel(self._logger.level)

        # Copy handlers
        for handler in self._logger.handlers:
            if not isinstance(handler, logging.handlers.SysLogHandler):
                handler.setFormatter(formatter)
                if handler not in bioblend_logger.handlers:
                    bioblend_logger.addHandler(handler)

        # Apply context filter to bioblend
        for filter in self._logger.filters:
            if filter not in bioblend_logger.filters:
                bioblend_logger.addFilter(filter)

        # Prevent duplicate logs
        bioblend_logger.propagate = False

    def _setup_syslog(self) -> None:
        """Set up syslog handler for system-level logging.

        Configures platform-specific syslog integration:
        - Linux: Uses /dev/log socket
        - macOS: Uses /var/run/syslog socket

        The syslog handler uses LOG_USER facility and includes process ID
        in the log format for better system integration.

        Note:
            If syslog setup fails, a warning is printed but logging continues
            with file-based logging only.

        """
        try:
            if platform.system() == "Linux":
                syslog_address = "/dev/log"
            elif platform.system() == "Darwin":  # macOS
                syslog_address = "/var/run/syslog"

            syslog_handler = logging.handlers.SysLogHandler(
                address=syslog_address, facility=logging.handlers.SysLogHandler.LOG_USER
            )
            syslog_formatter = logging.Formatter(
                "%(name)s[%(process)d]: %(levelname)-8s [%(galaxy)s@%(pulsar)s] %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
            syslog_handler.setFormatter(syslog_formatter)
            self._logger.addHandler(syslog_handler)

        except Exception as e:
            print(f"Warning: Could not setup syslog: {e}")

    def update_log_context(
        self, instance_name: str = "None", endpoint: str = "Default"
    ) -> None:
        """Update the logging context with Galaxy instance and endpoint information.

        This method updates the contextual information that gets injected into
        all subsequent log messages. The context includes the Galaxy instance
        name and associated endpoint, which helps track log messages across
        different test environments.

        Args:
            instance_name (str, optional): Name of the Galaxy instance being
                used for logging context. Defaults to "None".
            endpoint (str, optional): Endpoint associated with the Galaxy
                instance at that moment (e.g., Pulsar endpoint). Defaults to "Default".

        """
        # Update context dict
        self._log_context["GalaxyInstance"] = instance_name or "None"
        self._log_context["Endpoint"] = endpoint or "Default"

        # update filter
        self._logger.filters.clear()
        self._logger.addFilter(ContextFilter(self._log_context))

    # __getattr__ didn't cut it

    def debug(self, msg: object, *args: object, **kwargs: object) -> None:
        """Log a debug message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments passed to the underlying logger.

        """
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: object, *args: object, **kwargs: object) -> None:
        """Log an info message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments passed to the underlying logger.

        """
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: object, *args: object, **kwargs: object) -> None:
        """Log a warning message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments passed to the underlying logger.

        """
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: object, *args: object, **kwargs: object) -> None:
        """Log an error message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments passed to the underlying logger.

        """
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: object, *args: object, **kwargs: object) -> None:
        """Log a critical message.

        Args:
            msg: The message to log.
            *args: Positional arguments for message formatting.
            **kwargs: Keyword arguments passed to the underlying logger.

        """
        self._logger.critical(msg, *args, **kwargs)
