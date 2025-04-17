#!/usr/bin/env python3

import os
from pathlib import Path


#Globals variables

# Mock Functions
def mock_get_default_config_path() -> str:
    if os.name == 'nt':  # Windows
        base_path = Path(os.environ.get('APPDATA', Path.home()))
        config_dir = base_path / TOOL_NAME
    elif os.name == 'posix':  # Linux/Unix/macOS
        base_path = Path.home()
        if os.path.exists('/Library'):  # macOS
            config_dir = base_path / 'Library' / 'Application Support' / f'{TOOL_NAME}.yaml'
        else:  # Linux/Unix
            config_dir = base_path / '.config' / f'{TOOL_NAME}.yaml'

    return str(config_dir)


#Secure Config
TOOL_NAME="saber"


# Parser Defaults
P = "place_holder"
CONFIG_PATH = mock_get_default_config_path()

# Exit Codes
ERR_CODES = {"path": 1,
               "api": 3,
               "args":2,
               "tto": 42,
               "gal": 10,
               "job": 42}

# Example Config

example = """---
usegalaxy_instances:
  - name: Main
    url: "usegalaxy.examples"  # Replace with the actual instance URL
    api: "YOUR_API_KEY"  # Replace with a valid API key
    endpoints:
      - "changeme"  # Define the specific endpoints required
      - "changeme"
    # Optional: If authentication via email/password is needed, uncomment and set values
    # If API is defined it is always used first
    # email: "user@example.com"
    # password: "password"
    
    default_compute_id: "None"  # Default non-remote compute
    maxwait: 12000  # Upload timeout in seconds
    interval: 5  # Time (seconds) between uploads state checks
    sleep_time: 5 # Time between jobs states checks

# Global settings (can be overridden per instance)
ga_path: "/absolute/path"  # Define path to workflow .ga file
data_inputs:
  label_example_name:  # Change this key accordingly to the workflow used
    url: "change_me"  # Replace with the data source URL
    file_type: "change_me"  # Correct file type

timeout: 1200  # General timeout value, seconds
clean_history: onsuccess # Default. Other values: "never", "always"

"""
