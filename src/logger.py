import os
import logging
import platform
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
    def __init__(self, init_log_name: str = "saber"):
        self._log_context = {
            "GalaxyInstance": "None",
            "Endpoint": "None"
        }
        self._log_name = init_log_name

        # Initialize actual logger
        self._logger = None
        self._setup_logging()

    
    # Logging set up
    def _setup_logging(self):
        log_name = f"{self._log_name}.log"
        try:
            if os.geteuid() == 0:
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
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s [%(galaxy)s@%(pulsar)s] %(message)s','%Y-%m-%d %H:%M:%S')
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

        # Attach BioBlend logger to use the same handlers
        bioblend_logger = logging.getLogger("bioblend")
        bioblend_logger.setLevel(self._logger.level)
        for handler in self._logger.handlers:
            if not isinstance(handler, logging.handlers.SysLogHandler):
                handler.setFormatter(formatter)
                if handler not in bioblend_logger.handlers:
                    bioblend_logger.addHandler(handler)

        bioblend_logger.propagate = False



        # Setup syslog handler with platform-specific configuration
    def _setup_syslog(self):
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

