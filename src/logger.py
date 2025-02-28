#!/usr/bin/env python3

import os
import logging
import platform
from pathlib import Path
from platformdirs import user_log_dir


# Filters, from logging docs:
class ContextFilter(logging.Filter):
    """
    This is a filter which injects contextual dynbamic information into the log.

    In this case we are going to inject the values of a global variable that
    is updated as the test proceeds 
    """
    def __init__(self, context: dict):
        super().__init__()  # Initialize the parent class!
        self.context = context

    def filter(self, record):
        record.galaxy = self.context.get('GalaxyInstance', 'None')
        record.pulsar = self.context.get('Endpoint', 'Default')
        return True


class CustomLogger():
    '''
    Custom Logger

    :type init_log_name: str
    :param init_log_name: logger's name.
    '''
    def __init__(self, init_log_name: str, dir: Path = None):
        '''
        Custom Logger

        :type init_log_name: str
        :param init_log_name: logger's name.
        '''
        self._log_context = {
            "GalaxyInstance": "None",
            "Endpoint": "None"
        }
        self._log_name = init_log_name

        # Initialize actual logger
        self._logger = None
        self._setup_logging(dir)

    

    def _setup_logging(self, log_dir: Path = None):
        '''
        Set up logging with customs formatter, handlers and syslog.
        Log are set up with file rotation: every midnight if file is older than 7 day 
        or heavier than 10MB 
        Default log paths depends on user.
        '''
        log_name = f"{self._log_name}.log"
        try:
            if log_dir is not None:
                log_dir = (log_dir.parent / log_dir.stem) if log_dir.suffix != "" else log_dir
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


        #Setting up handler for rotating logs and custom format
        handler = logging.handlers.TimedRotatingFileHandler(log_file, when="midnight", backupCount=7)
        formatter = logging.Formatter('%(asctime)s %(name)s: %(levelname)-8s [%(galaxy)s@%(pulsar)s] %(message)s','%Y-%m-%d %H:%M:%S')
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

        # TODO: Fix this
        # Attach BioBlend logger to use the same handlers
        bioblend_logger = logging.getLogger("bioblend")
        bioblend_logger.setLevel(self._logger.level)
        for handler in self._logger.handlers:
            if not isinstance(handler, logging.handlers.SysLogHandler):
                handler.setFormatter(formatter)
                if handler not in bioblend_logger.handlers:
                    bioblend_logger.addHandler(handler)

        bioblend_logger.propagate = False



    def _setup_syslog(self):
        '''
        Set up syslog handler
        '''
        try:
            if platform.system() == "Linux":
                syslog_address = "/dev/log"
            elif platform.system() == "Darwin":  # macOS
                syslog_address = "/var/run/syslog"

            syslog_handler = logging.handlers.SysLogHandler(
                address=syslog_address,
                facility=logging.handlers.SysLogHandler.LOG_USER
            )
            syslog_formatter = logging.Formatter('%(name)s[%(process)d]: %(levelname)-8s [%(galaxy)s@%(pulsar)s] %(message)s','%Y-%m-%d %H:%M:%S')
            syslog_handler.setFormatter(syslog_formatter)
            self._logger.addHandler(syslog_handler)

        except Exception as e:
            print(f"Warning: Could not setup syslog: {e}")

        
   
    def update_log_context(self, instance_name: str = "None", endpoint: str = "Default"):
        '''
        Updates the logging context with the specified instance name and endpoint.

        :param instance_name: The name of the Galaxy instance to be logged. Defaults to "None".
        :type instance_name: str, optional
        :param endpoint: The endpoint associated with the Galaxy instance. Defaults to "Default".
        :type endpoint: str, optional
        '''
        # Update context dict
        self._log_context['GalaxyInstance'] = instance_name or "None"
        self._log_context['Endpoint'] = endpoint or "Default"

        #update filter
        self._logger.filters.clear()
        self._logger.addFilter(ContextFilter(self._log_context))


# __getattr__ didn't cut it
# Only the common method are delegated

    def debug(self, msg, *args, **kwargs):
        self._logger.debug(msg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._logger.warning(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)
    
    def critical(self, msg, *args, **kwargs):
        self._logger.critical(msg, *args, **kwargs)

