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
        self.group = self.parser.add_mutually_exclusive_group()
        self.group.add_argument('-e', '--edit', metavar='PATH', type=Path, help='Open the default editor to edit the existing encrypted YAML file,\
                                                            \nalways encrypt the file after editing. Defaults to nano.')
        self.group.add_argument('-c', '--encrypt', metavar='PATH', type=Path, help='Encrypt a YAML file.')
        self.group.add_argument('-d', '--decrypt', metavar='PATH', type=Path, help='Decrypt a YAML file.')
        self.group.add_argument('-s', '--settings', metavar='PATH', type=Path, default=CONFIG_PATH,
                        help=f'Specify path for settings YAML file. Defaults to {CONFIG_PATH}')
        self.group.add_argument('-x', '--example_settings', action='store_true', help='Prints an example configuration')
        self.group.add_argument('-r', '--html_report', metavar='PATH', type=Path,
                            default=Path.home().joinpath(f'saber_report_{datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.html'), 
                                                        help='Enables HTML report, it accepts a path for the output:/path/report.html\
                                                            \nDefaults to \'~/saber_report_YYYY-MM-DD_HH-MM-SS.html\' otherwise.')
        args = self.parser.parse_args()
        self.editable = vars(args)
        self._necessarily_inclusive()
        #a bunch of other functions
        return argparse.Namespace(**self.editable) 



    def _necessarily_inclusive(self) -> None:
        for a in self.editable['edit', 'encrypt', 'decrypt']:
            if (a is not None) and (self.editable['password'] == P):
                self.parser.error("This argument always requires -p/--password")
        pass



    def _set_password(self) -> None:
        if (self.editable['password'] == P) and (os.getenv('SABER_PASSWORD', None) is not None):
            self.editable['password'] = os.getenv('SABER_PASSWORD')




    def _check_password_type(self) -> None:
        raw_pw = Path(self.editable['password'])
        if raw_pw.is_file():
            with open(raw_pw, 'r') as f:
                self.editable['password'] = f.read()
    


    def _output_check(self):
        if (Path(self.editable['html_report']).suffix == '.html') and (Path(self.editable['html_report']).parent.is_dir()):
            pass
        self.parser.error(f"This argument is not a valid path for the HTML output")



    def _safety_check(self, args_path: Path) -> None:
        if (args_path.suffix == ".yaml") and (args_path.is_file()):
            pass
        self.parser.error(f"This argument is not a valid YAML file")


    @staticmethod
    def _path_resolver(path: Path) -> Path:
        if path is not None:
            path = Path(path)
            path = path.expanduser() if not path.is_absolute() else path
            if not path.is_absolute():
                path = Path.home() / path
            path = path.resolve()
            return path
        return None



