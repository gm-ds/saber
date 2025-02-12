# SABER
 Systematic API Benchmark for (pulsar) Endpoint Reliability
 
>**:warning: Work in Progress**

## TODO
- Improve logging
- Multiple Job Support
- Telegraf support
- Comment and Docs
- ~~Switch to yaml config file to not rely on input.json~~

## Configuration
Place the yaml file in the same working directory as the script. Edit its name to `pulsar_test_conf.yaml` and adjust the variables.
All variables under `usegalaxy_instances` will overwrite upper level values, leaving the possibility to tailor test jobs between Galaxy instance and Pulsar Endpoint.
A workflow file is still needed.
