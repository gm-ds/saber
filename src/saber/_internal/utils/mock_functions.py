#!/usr/bin/env python3

"""Mock functions for testing and development purposes.

This module provides mock implementations of functions used in saber for
situations where full functionality is not required or available.

Functions:
    mock_get_default_config_path: Returns platform-specific default
        configuration file paths.
"""

import os
from pathlib import Path

from saber._internal.utils.globals import TOOL_NAME


# Mock Functions
def _mock_get_default_config_path() -> str:
    """Get the default configuration file path for the current platform.

    This mock function determines the appropriate configuration file location
    based on the operating system, following platform conventions for
    application configuration storage.

    Returns:
        str: The absolute path to the default configuration file location.
            - Windows: %APPDATA%/saber/
            - macOS: ~/Library/Application Support/saber/settings.yml
            - Linux/Unix: ~/.config/saber/settings.yaml

    Raises:
        None: This function handles missing environment variables gracefully
            by falling back to the user's home directory.

    Example:
        >>> path = mock_get_default_config_path()
        >>> print(path)
        '/home/user/.config/saber/settings.yaml'  # On Linux

    Note:
        This is a mock function intended for testing, development, string display.
        Its results are not validated.

    """
    if os.name == "nt":  # Windows
        base_path = Path(os.environ.get("APPDATA", Path.home()))
        config_dir = base_path / TOOL_NAME
    elif os.name == "posix":  # Linux/Unix/macOS
        base_path = Path.home()
        if os.path.exists("/Library"):  # macOS
            config_dir = (
                base_path
                / "Library"
                / "Application Support"
                / f"{TOOL_NAME}"
                / "settings.yml"
            )
        else:  # Linux/Unix
            config_dir = base_path / ".config" / f"{TOOL_NAME}" / "settings.yaml"

    return str(config_dir)
