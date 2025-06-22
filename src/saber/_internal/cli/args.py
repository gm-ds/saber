#!/usr/bin/env python3
"""Command-line argument parser for the Saber tool.

This module provides a Parser class that handles command-line arguments for testing
multiple useGalaxy instances and Pulsar Endpoints. It includes support for encrypted
configuration files, various output formats, and validation.
"""

import argparse
import os
from datetime import datetime
from pathlib import Path

HTML_DEFAULT = Path.home().joinpath(
    f"saber_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.html"
)
TABLE_DEFAULT = Path.home().joinpath(
    f"saber_summary_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.html"
)
MD_DEFAULT = Path.home().joinpath(
    f"saber_report_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.md"
)


class _parser:
    """Command-line argument parser for the Saber testing tool.

    This class handles parsing and validation of command-line arguments. It supports
    YAML configuration files, multiple output formats, and comprehensive
    path validation.

    Attributes:
        place_holder (str): Placeholder value for unset passwords.
        parser (argparse.ArgumentParser): The main argument parser instance.
        editable (dict): Dictionary containing parsed and processed arguments.
        group (argparse._MutuallyExclusiveGroup): Mutually exclusive argument group.

    Args:
        place_holder (str): Placeholder string used for default password value.
        mock_conf_path (str): Default path for configuration file.

    Example:
        >>> parser = _parser("default_placeholder", "/path/to/config.yml")
        >>> args = parser.arguments()

    """

    def __init__(self, place_holder: str, mock_conf_path: str) -> None:
        """Initialize the Parser with default values and configure all arguments.

        Sets up the argument parser with all available options, processes the
        arguments, and performs validation checks.

        Args:
            place_holder (str): Default placeholder value for password field.
            mock_conf_path (str): Default path to the configuration YAML file.

        Returns:
            None
        """
        self.place_holder = place_holder
        self.parser = argparse.ArgumentParser(
            description="Tool to test multiple useGalaxy instances and Pulsar Endpoints"
        )

        # Configure all command-line arguments
        self._setup_arguments(mock_conf_path)

        # Parse and process arguments
        args = self.parser.parse_args()
        self.editable = vars(args)

        # Perform validation and processing
        self._set_password()
        self._check_password_type()
        self._custom_args_validation()
        self.val_safety_check()
        self._output_check()

    def _setup_arguments(self, mock_conf_path: str) -> None:
        """Configure all command-line arguments for the parser.

        Sets up individual arguments and mutually exclusive groups for the
        argument parser instance.

        Args:
            mock_conf_path (str): Default configuration file path for help text.

        """
        self.parser.add_argument(
            "-p",
            "--password",
            default=self.place_holder,
            help="Password to decrypt and encrypt the settings YAML file. "
            "Accepts txt files and strings",
        )
        self.parser.add_argument(
            "-j",
            "--print_json",
            action="store_true",
            help="Prints results as a JSON dictionary",
        )
        self.parser.add_argument(
            "-r",
            "--html_report",
            metavar="PATH",
            type=Path,
            nargs="?",
            const=HTML_DEFAULT,
            help="Enables HTML report, it accepts a path for the output:/path/report.html "
            "Defaults to '~/saber_report_YYYY-MM-DD_HH-MM-SS.html' otherwise.",
        )
        self.parser.add_argument(
            "-m",
            "--md_report",
            metavar="PATH",
            type=Path,
            nargs="?",
            const=MD_DEFAULT,
            help="Enables Markdown report, it accepts a path for the output:/path/report.md "
            "Defaults to '~/saber_report_YYYY-MM-DD_HH-MM-SS.md' otherwise.",
        )
        self.parser.add_argument(
            "-t",
            "--table_html_report",
            metavar="PATH",
            type=Path,
            nargs="?",
            const=TABLE_DEFAULT,
            help="Enables HTML summary report, it accepts a path for the output:/path/report.html "
            "Defaults to '~/saber_summary_YYYY-MM-DD_HH-MM-SS.html' otherwise.",
        )
        self.parser.add_argument(
            "-l",
            "--log_dir",
            metavar="LOG DIRECTORY",
            type=Path,
            help="Custom log DIRECTORY. Defaults depends on the platform. "
            'MacOS: "/Users/<your-user>/Library/Logs/<tool-name>" '
            'Windows: "C:\\Users\\<your-user>\\<tool-name>\\Local\\Acme\\<tool-name>\\Logs" '
            'Linux: "/home/<your-user>/.local/state/<tool-name>/log"',
        )

        # Mutually exclusive group for file operations
        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument(
            "-e",
            "--edit",
            metavar="PATH",
            type=Path,
            help="Open the default editor to edit the existing encrypted YAML file, "
            "always encrypt the file after editing. Defaults to nano.",
        )
        self.group.add_argument(
            "-c", "--encrypt", metavar="PATH", type=Path, help="Encrypt a YAML file."
        )
        self.group.add_argument(
            "-d", "--decrypt", metavar="PATH", type=Path, help="Decrypt a YAML file."
        )
        self.group.add_argument(
            "-s",
            "--settings",
            metavar="PATH",
            type=Path,
            help=f"Specify path for settings YAML file. Defaults to {mock_conf_path}",
        )
        self.group.add_argument(
            "-x",
            "--example_settings",
            action="store_true",
            help="Prints an example configuration, all other arguments are ignored",
        )

    def arguments(self) -> argparse.Namespace:
        """Return the processed arguments as an argparse Namespace object.

        Returns:
            argparse.Namespace: Namespace object containing all processed command-line arguments.

        Example:
            >>> parser = Parser("placeholder", "/config/path")
            >>> args = parser.arguments()
            >>> print(f"HTML report path: {args.html_report}")

        """
        return argparse.Namespace(**self.editable)

    def _custom_args_validation(self) -> None:
        """Validate custom argument combinations and dependencies.

        Ensures that operations requiring passwords (edit, encrypt, decrypt) have
        a password provided. If example_settings is requested, all other arguments
        are cleared except for the example_settings flag.

        Raises:
            argparse.ArgumentError: If a required password argument is missing when
                                  performing operations that require encryption/decryption.

        Note:
            When example_settings is True, all other arguments are reset to None
            to prevent conflicts during example generation.

        """
        for a in [
            self.editable["edit"],
            self.editable["encrypt"],
            self.editable["decrypt"],
        ]:
            if a is not None:
                if self.editable["password"] == self.place_holder:
                    self.parser.error("This argument always requires -p/--password")
        if self.editable["example_settings"]:
            tmp = self.editable["example_settings"]
            self.editable = {key: None for key in self.editable}
            self.editable["example_settings"] = tmp

    def _set_password(self) -> None:
        """Set password from environment variable if available.

        Checks for the SABER_PASSWORD environment variable and uses it as the
        password if no password was provided via command line arguments.
        Strips whitespace from the environment variable value.

        Environment Variables:
            SABER_PASSWORD: Password value to use for encryption/decryption operations.

        Note:
            Environment variable takes precedence only when no password is explicitly
            provided via command-line arguments.

        """
        temp_pswd = os.getenv("SABER_PASSWORD")
        if self.editable["password"] == self.place_holder and temp_pswd is not None:
            self.editable["password"] = temp_pswd
            self.editable["password"] = self.editable["password"].strip()

    def _check_password_type(self) -> None:
        """Process password argument to handle file-based passwords.

        If the password argument points to a file path, reads the file content
        and uses it as the password.

        Note:
            If the password argument is a valid file path, the entire file content
            is read and used as the password. The file should contain only the
            password without additional formatting.

        """
        if self.editable["password"] is not None:
            if self.editable["password"] != self.place_holder:
                tmp = {}
                tmp["path"] = self._path_resolver(self.editable["password"], "path")
                if tmp["path"].is_file():
                    with open(tmp["path"], "r") as f:
                        self.editable["password"] = f.read()

    def _output_check(
        self, output_list: list = ["html_report", "table_html_report", "md_report"]
    ) -> None:
        """Validate output file paths for HTML and Markdown reports.

        Checks that output paths have valid extensions (.html or .md) and that
        the parent directories exist.

        Args:
            output_list (list, optional): List of output argument keys to validate.
                                        Defaults to ["html_report", "table_html_report", "md_report"].

        Returns:
            None

        Raises:
            argparse.ArgumentError: If any output path is invalid (wrong extension
                                  or parent directory doesn't exist).

        Note:
            Valid extensions are .html for HTML reports and .md for Markdown reports.
            Parent directories must exist before the tool runs.

        """
        for key in output_list:
            if self.editable[key] is not None:
                self._path_resolver(self.editable[key], key)
                parent_o = self.editable[key].parent
                suff = self.editable[key].suffix in [".html", ".md"]
                dir = parent_o.is_dir()
                if suff and dir:
                    pass
                else:
                    self.parser.error(
                        "This argument is not a valid path for the HTML or MD output"
                    )

    def val_safety_check(self) -> None:
        """Validates YAML file paths and resolves the log directory path.

        Skips validation if example_settings is requested.

        Returns:
            None


        Note:
            This method coordinates validation of different argument types and
            ensures all file paths are properly resolved and validated.

        """
        if self.editable["example_settings"]:
            pass
        else:
            paths = [
                (self.editable["edit"], "edit"),
                (self.editable["encrypt"], "encrypt"),
                (self.editable["decrypt"], "decrypt"),
                (self.editable["settings"], "settings"),
            ]
            self._safety_check(paths)
            self._path_resolver(self.editable["log_dir"], "log_dir")

    def _safety_check(self, args_path: list) -> None:
        """Validate YAML file paths and extensions.

        Ensures that file arguments point to valid YAML files with correct
        extensions (.yaml or .yml) and that the files exist.

        Args:
            args_path (list): List of tuples containing (path, key) pairs to validate.
                            Each tuple contains a Path object and its corresponding
                            argument key name.

        Raises:
            argparse.ArgumentError: If any path doesn't point to a valid YAML file
                                  or if the file doesn't exist.

        Note:
            Only validates paths that are not None. Accepted extensions are
            .yaml and .yml (case-sensitive).

        """
        for p in args_path:
            if isinstance(p[0], Path) and p[0] is not None:
                self._path_resolver(p[0], p[1])
                if p[0].suffix in (".yaml", ".yml") and p[0].is_file():
                    pass
                else:
                    self.parser.error("This Path does not point to a valid YAML file")

    def _path_resolver(self, value: any, key: str) -> Path:
        """Resolve file paths to absolute paths with user directory expansion.

        Converts relative paths to absolute paths, expands user directory
        shortcuts (~), and updates the internal argument dictionary.

        Args:
            value: The path value to resolve (can be Path, str, or None).
            key (str): The argument key name for updating the internal dictionary.

        Returns:
            Path: Resolved absolute path, or None if input value is None.
                 When key matches known argument names, returns None as the
                 path is stored in the internal dictionary.

        Note:
            For known argument keys (edit, encrypt, decrypt, settings, html_report,
            table_html_report, md_report, log_dir), the resolved path is stored
            in the internal editable dictionary and None is returned.
            For other keys, the resolved Path object is returned directly.

        """
        if value is not None:
            if not isinstance(value, Path):
                value = Path(value)
            value = value.expanduser()
            value = value.resolve()

            if key in [
                "edit",
                "encrypt",
                "decrypt",
                "settings",
                "html_report",
                "table_html_report",
                "md_report",
                "log_dir",
            ]:
                self.editable[key] = value
                return None
            else:
                return value
        return None
