#!/usr/bin/env python3

import os
from pathlib import Path

from saber._internal.utils.globals import TOOL_NAME


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
