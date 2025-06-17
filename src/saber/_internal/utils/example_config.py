#!/usr/bin/env python3

"""Example configuration template for SABER.

This module contains a template YAML configuration that demonstrates how to
set up Galaxy instances, API keys, data inputs, and various timeout settings.

The configuration template includes:
    - Galaxy instance settings with API authentication
    - Endpoint definitions for workflow execution
    - Data input specifications with URLs and file types
    - Timeout and polling interval configurations

Attributes:
    _example (str): A multi-line YAML string containing the complete
        configuration template with placeholder values and comments
        explaining each section.

"""

example = """

---
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
clean_history: onsuccess # Default. Other values: "never", "always", "successful_only". The 
                            # last option removes all datasets of successful jobs and if all jobs
                            # are successful it clears the history (as "onsuccess")

"""
