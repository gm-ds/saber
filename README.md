# SABER
 Systematic API Benchmark for (Pulsar) Endpoint Reliability
 
>**:warning: Work in Progress**

## Configuration
An example of configuration can be found in the `configs` folder. Edit its name to `settings.yaml` and adjust the variables.
All variables under `usegalaxy_instances` will overwrite upper level values, leaving the possibility to tailor test jobs between Galaxy instances and Pulsar Endpoints.
A workflow file is still needed.

## Logs
SABER can be run as root, in that case the logs can be found in `var/log/saber/saber.log` otherwhise in `~/.local/share/state/saber/log/saber.log`. For the path in other platforms check this [documentation](https://pypi.org/project/appdirs/).

A brief log example:

 ```
2025-02-14 15:12:31,070 INFO     [usegalaxy@TBD] Updating pulsar endpoint in user preferences
2025-02-14 15:12:31,210 INFO     [usegalaxy@Default] Testing pulsar endpoint Default from usegalaxy instance
2025-02-14 15:13:14,173 INFO     [usegalaxy@example] Testing pulsar endpoint example from usegalaxy instance
```
The Galaxy server being currently tested is displayed in brackets along with the pulsar endpoint. The `TBD` values is used during Galaxy Instance initialization. The `Default` endpoint correspond to the local compute of the server, it is used during dataset uploads.

## TODO
- REFACTOR
- Multiple Job Support
- Improve errors handling
- InfluxDB support
- Comments and Docs
- ~~Switch to yaml config file to not rely on input.json~~
- ~~Improve logging~~