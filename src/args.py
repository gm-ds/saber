#!/usr/bin/env python3

import os
import argparse
from pathlib import Path
from datetime import datetime


class Parser():
    def __init__(self, place_holder: str, mock_conf_path: str):
        self.place_holder = place_holder
        self.parser = argparse.ArgumentParser(description="Tool to test multiple useGalaxy instances and Pulsar Endpoints")
        self.parser.add_argument('-p', '--password', default=self.place_holder, help='Password to decrypt and encrypt the settings YAML file.\
                            \nAccepts txt files and strings')
        self.parser.add_argument('-i', '--influxdb', action='store_true', help='Send metrics to InfluxDB when the argument is used.\
                                  Credentials must be defined in configuration file.')
        self.parser.add_argument('-r', '--html_report', metavar='PATH', type=Path, nargs='?',
                            default=Path.joinpath(Path.home(), f'saber_report_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.html'), 
                                                        help='Enables HTML report, it accepts a path for the output:/path/report.html\
                                                            \nDefaults to \'~/saber_report_YYYY-MM-DD_HH-MM-SS.html\' otherwise.')
        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument('-e', '--edit', metavar='PATH', type=Path, help='Open the default editor to edit the existing encrypted YAML file,\
                                                            \nalways encrypt the file after editing. Defaults to nano.')
        self.group.add_argument('-c', '--encrypt', metavar='PATH', type=Path, help='Encrypt a YAML file.')
        self.group.add_argument('-d', '--decrypt', metavar='PATH', type=Path, help='Decrypt a YAML file.')
        self.group.add_argument('-s', '--settings', metavar='PATH', type=Path,
                        help=f'Specify path for settings YAML file. Defaults to {mock_conf_path}')
        self.group.add_argument('-x', '--example_settings', action='store_true', help='Prints an example configuration, all other arguments are ignored')

        args = self.parser.parse_args()
        self.editable = vars(args)
        self._set_password()
        self._check_password_type()
        self._custom_args_validation()
        self.val_safety_check()
        self._output_check()
        


    def arguments(self) -> argparse.Namespace:
        '''
        Return argparse Namespace.
        '''
        return argparse.Namespace(**self.editable) 



    def _custom_args_validation(self) -> None:
        '''
        Validates arguments and ensures dependencies.

        If the `example_settings` argument is set, it replaces the `editable` 
        dictionary with its contents, overriding all other arguemnts.

        :raises argparse.ArgumentError: If a required password argument is missing when needed.
        '''
        for a in [self.editable['edit'], self.editable['encrypt'], self.editable['decrypt']]:
            if a is not None:
                if (self.editable['password'] == self.place_holder):
                    self.parser.error("This argument always requires -p/--password")
        if self.editable['example_settings']:
                tmp = self.editable['example_settings']
                self.editable = {key: None for key in self.editable}
                self.editable['example_settings'] = tmp




    def _set_password(self) -> None:
        '''
        Set password from environ if SABER_PASSWORD is defined when password is not set through argsparse.
        '''
        temp_pswd = os.getenv('SABER_PASSWORD')
        if self.editable['password'] == self.place_holder and  temp_pswd is not None:
            self.editable['password'] = temp_pswd



    def _check_password_type(self) -> None:
        '''
        If password given is a path to a file, its content are used.
        '''
        if self.editable['password'] != None:
            if self.editable['password'] != self.place_holder:
                self._path_resolver(self.editable['password'], 'password')
                if isinstance(self.editable['password'], Path) and self.editable['password'].is_file():
                    with open(self.editable['password'], 'r') as f:
                        self.editable['password'] = f.read()
                else:
                    self.editable['password'] = str(self.editable['password'])
        


    def _output_check(self):
        '''
        Check validity of the path given for the HTML output.
        '''
        if self.editable['html_report'] != None:
            self._path_resolver(self.editable['html_report'], 'html_report')
            parent_o = self.editable['html_report'].parent
            suff = self.editable['html_report'].suffix == '.html'
            dir = parent_o.is_dir()
            if suff and dir:
                pass
            else:
                self.parser.error(f"This argument is not a valid path for the HTML output")


    def val_safety_check(self):
        '''
        Wrapper to pass value, key tuples.
        '''
        if self.editable:
            pass
        else:
            paths = [
                (self.editable['edit'], 'edit'),
                (self.editable['encrypt'], 'encrypt'), 
                (self.editable['decrypt'], 'decrypt'), 
                (self.editable['settings'], 'settings')
            ]
            self._safety_check(paths)



    def _safety_check(self, args_path: list) -> None:
        '''
        Checks the type of a given file.
        Non YAML files fail the check.

        :param args_path: The YAML file path to check.
        :type args_path: Path
        '''
        for p in args_path:
            if isinstance(p[0], Path) and p[0] is not None:
                self._path_resolver(p[0], p[1])
                if p[0].suffix in (".yaml", ".yml") and p[1].is_file():
                    pass
                else:
                    self.parser.error("This Path does not point to a valid YAML file")



    def _path_resolver(self, value: Path, key: str) -> Path:
        '''
        Resolves a given file path to an absolute path.

        :param path: The file path to resolve.
        :type path: Path
        :return: The resolved absolute file path.
        :rtype: Path
        '''
        if value is not None:
            if not isinstance(value, Path):
                value = Path(value)
            value = value.expanduser() if not value.is_absolute() else value
            if not value.is_absolute():
                value = Path.home() / value
                value = value.resolve()
                self.editable[key] = value



