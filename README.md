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
    Generate an HTML report. Accepts a custom file path. Default: ~/saber_report_YYYY-MM-DD_HH-MM-SS.html
    Not yet implemented

### Mutually Exclusive Group

- `-e`, `--edit`
    Open and edit an encrypted YAML file (auto-encrypt after editing). Not yet thoroughly tested.

- `-c`, `--encrypt`
    Encrypt a given YAML file. Not yet thoroughly tested.

- `-d`, `--decrypt`
    Decrypt a given YAML file. Not yet thoroughly tested.

- `-s`, `--settings`
    Specify the settings YAML file path. Default: `~/.config/saber/settings.yaml`

- `-x`, `--example_settings`
    Print an example configuration.


## Configuration
An example of configuration can be printed using the `-x` argument when launching the script. By default SABER will try to search in `~/.config/saber/settings.yaml` or `.yaml`. If the file is not found it prints an error message.

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
- HTML report
- Multiple Job Support; WIP
- Improve errors handling
- InfluxDB support
- ~~Comments and Docs~~
- ~~Switch to yaml config file to not rely on input.json~~
- ~~Improve logging~~
- ~~REFACTOR~~
- ~~argparse~~
