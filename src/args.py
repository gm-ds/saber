#!/usr/bin/env python3

import os
import argparse
from globals import P, CONFIG_PATH
from pathlib import Path
from datetime import datetime


class Parser():
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="Tool to test multiple useGalaxy instances and Pulsar Endpoints")
        self.parser.add_argument('-p', '--password', default=P, help='Password to decrypt and encrypt the settings YAML file.\
                            \nAccepts txt files and strings')
        self.parser.add_argument('-i', '--influxdb', action='store_true', help='Send metrics to InfluxDB when the argument is used.\
                                  Credentials must be defined in configuration file.')
        self.parser.add_argument('-r', '--html_report', metavar='PATH', type=Path,
                            default=Path.home().joinpath(f'saber_report_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.html'), 
                                                        help='Enables HTML report, it accepts a path for the output:/path/report.html\
                                                            \nDefaults to \'~/saber_report_YYYY-MM-DD_HH-MM-SS.html\' otherwise.')
        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument('-e', '--edit', metavar='PATH', type=Path, help='Open the default editor to edit the existing encrypted YAML file,\
                                                            \nalways encrypt the file after editing. Defaults to nano.')
        self.group.add_argument('-c', '--encrypt', metavar='PATH', type=Path, help='Encrypt a YAML file.')
        self.group.add_argument('-d', '--decrypt', metavar='PATH', type=Path, help='Decrypt a YAML file.')
        self.group.add_argument('-s', '--settings', metavar='PATH', type=Path,
                        help=f'Specify path for settings YAML file. Defaults to {CONFIG_PATH}')
        self.group.add_argument('-x', '--example_settings', action='store_true', help='Prints an example configuration, all other arguments are ignored')

        args = self.parser.parse_args()
        self.editable = vars(args)
        self._custom_args_validation()
        self._set_password()
        self._check_password_type()
        self._safety_check(self.editable['edit','encrypt','decrypt','settings'])
        self._output_check()
        return argparse.Namespace(**self.editable) 



    def _custom_args_validation(self) -> None:
        '''
        Validates arguments and ensures dependencies.

        If the `example_settings` argument is set, it replaces the `editable` 
        dictionary with its contents, overriding all other arguemnts.

        :raises argparse.ArgumentError: If a required password argument is missing when needed.
        '''
        for a in self.editable['edit', 'encrypt', 'decrypt']:
            if a is not None:
                if (self.editable['password'] == P):
                    self.parser.error("This argument always requires -p/--password")
        if self.editable['example_settings']:
                self.editable = self.editable['example_settings']




    def _set_password(self) -> None:
        '''
        Set password from environ if SABER_PASSWORD is defined when password is not set through argsparse.
        '''
        if (self.editable['password'] == P) and (os.getenv('SABER_PASSWORD', None) is not None):
            self.editable['password'] = os.getenv('SABER_PASSWORD')





    def _check_password_type(self) -> None:
        '''
        If password given is a path to a file, its content are used.
        '''
        self._path_resolver(self.editable['password'])
        if self.editable['password'].is_file():
            with open(self.editable['password'], 'r') as f:
                self.editable['password'] = f.read()
    


    def _output_check(self):
        '''
        Check validity of the path given for the HTML output.
        '''
        self._path_resolver(self.editable['html_report'])
        if (self.editable['html_report'].suffix == '.html') and (self.editable['html_report'].parent.is_dir()):
            pass
        self.parser.error(f"This argument is not a valid path for the HTML output")



    def _safety_check(self, args_path: list) -> None:
        '''
        Checks the type of a given file.
        Non YAML files fail the check.

        :param args_path: The YAML file path to check.
        :type args_path: Path
        '''
        for p in args_path:
            if p is not None:
                self._path_resolver(p)
                if p.suffix in (".yaml", ".yml") and (p.is_file()):
                    pass
                self.parser.error(f"This Path does not point to a valid YAML file")



    def _path_resolver(self, path: Path) -> Path:
        '''
        Resolves a given file path to an absolute path.

        :param path: The file path to resolve.
        :type path: Path
        :return: The resolved absolute file path.
        :rtype: Path
        '''
        if path is not None or isinstance(path, Path):
            path = Path(path)
        path = path.expanduser() if not path.is_absolute() else path
        if not path.is_absolute():
            path = Path.home() / path
            path = path.resolve()



