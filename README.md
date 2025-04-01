# SABER
 Systematic API Benchmark for (Pulsar) Endpoint Reliability
 
>**:warning: Work in Progress**
>
>Use at your own risk.

## CLI arguments

- `-p`, `--password`
    Password for encrypting/decrypting the settings YAML file. Always required with `-e`, `-c`, `-d` and if the settings are encrypted.

- `-r`, `--html_report`
    Generates an HTML report. Accepts a custom file path. Default: ~/saber_report_YYYY-MM-DD_HH-MM-SS.html

- `-m`, `--md_report`
    Generates a Markdown report. Accepts a custom file path. Default: ~/saber_report_YYYY-MM-DD_HH-MM-SS.md

- `-t`, `--table_html_report`
    Generates an HTML summarized report in form of a table. Accepts a custom file path. Default: ~/saber_summary_YYYY-MM-DD_HH-MM-SS.html

- `-l`, `--log_dir`
    Generates the log file in the given directory. If a file path is given instead of a directory, the name of the file, without suffix, is used to make a new directory for `saber.log`.

### Mutually Exclusive Group

- `-e`, `--edit`
    Opens and edits an encrypted YAML file (auto-encrypt after editing). It uses the editor defined in the EDITOR environment variable, if EDITOR is not set it will fallback on `nano`.

- `-c`, `--encrypt`
    Encrypts a given YAML file.

- `-d`, `--decrypt`
    Decrypts a given YAML file.

- `-s`, `--settings`
    Custom settings YAML file path. Default: `~/.config/saber/settings.yaml`

- `-x`, `--example_settings`
    Prints an example configuration.


## Configuration
An example of configuration can be printed using the `-x` argument when launching the script, the same example can be found in the root of this repository. By default SABER will try to search for `~/.config/saber/settings.yaml` or `.yml`. If the file is not found it prints an error message.

All variables under `usegalaxy_instances` will overwrite upper level values, leaving the possibility to tailor test jobs between Galaxy instances and Pulsar Endpoints.
A workflow file is still needed.

`maxwait` and `timeout` define how long SABER should wait for an upload or job execution to complete.
`interval` and `sleep_time` specify the delay between status checks during uploads and job monitoring, respectively.

## Logs
SABER can be run as root, in that case the logs can be found in `/var/log/saber/saber.log` otherwhise in `~/.local/state/saber/log/saber.log`. For the path in other platforms check this [documentation](https://pypi.org/project/appdirs/). 
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
- Clean jinja2 templates
