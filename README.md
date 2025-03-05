# SABER
 Systematic API Benchmark for (Pulsar) Endpoint Reliability
 
>**:warning: Work in Progress**
>
>Use at your own risk.

## CLI arguments

- `-p`, `--password`
    Password for encrypting/decrypting the settings YAML file. Always required with `-e`, `-c`, `-d` and if the settings are encrypted.

- `-i`, ``--influxdb``
    Send metrics to InfluxDB (requires credentials in the config file).
    Not yet implemented

- `-r`, `--html_report`
    Generates an HTML report. Accepts a custom file path. Default: ~/saber_report_YYYY-MM-DD_HH-MM-SS.html
    Implementation in progress

- `-l`, `--log_dr`
    Generates the log file in the given directory. If a file path is given instead of a directory, the name of the file, without suffix, is used to make a new directory for `saber.log`.

### Mutually Exclusive Group

- `-e`, `--edit`
    Opens and edits an encrypted YAML file (auto-encrypt after editing). Not yet thoroughly tested.

- `-c`, `--encrypt`
    Encrypts a given YAML file. Not yet thoroughly tested.

- `-d`, `--decrypt`
    Decrypts a given YAML file. Not yet thoroughly tested.

- `-s`, `--settings`
    Custom settings YAML file path. Default: `~/.config/saber/settings.yaml`

- `-x`, `--example_settings`
    Prints an example configuration.


## Configuration
An example of configuration can be printed using the `-x` argument when launching the script, the same example can be found in the root of this repository. By default SABER will try to search in `~/.config/saber/settings.yaml` or `.yaml`. If the file is not found it prints an error message.

All variables under `usegalaxy_instances` will overwrite upper level values, leaving the possibility to tailor test jobs between Galaxy instances and Pulsar Endpoints.
A workflow file is still needed.

## Logs
SABER can be run as root, in that case the logs can be found in `var/log/saber/saber.log` otherwhise in `~/.local/state/saber/log/saber.log`. For the path in other platforms check this [documentation](https://pypi.org/project/appdirs/). 
The log is also added to syslog.

A brief log example:

 ```
2025-02-14 15:12:31,070 INFO     [usegalaxy@TBD] Updating pulsar endpoint in user preferences
2025-02-14 15:12:31,210 INFO     [usegalaxy@Default] Testing pulsar endpoint Default from usegalaxy instance
2025-02-14 15:13:14,173 INFO     [usegalaxy@example] Testing pulsar endpoint example from usegalaxy instance
```
The Galaxy server being currently tested is displayed in brackets along with the pulsar endpoint. The `TBD` values is used during Galaxy Instance initialization. The `Default` endpoint correspond to the local compute of the server, it is used during dataset uploads.

## TODO
- Improve errors handling
- InfluxDB support
- ~~Comments and Docs~~
- ~~Switch to yaml config file to not rely on input.json~~
- ~~Improve logging~~
- ~~REFACTOR~~
- ~~argparse~~
- ~~Multiple Job Support; WIP~~
- ~~HTML report~~


