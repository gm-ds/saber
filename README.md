# SABER

**Systematic API Benchmark for (Pulsar) Endpoint Reliability**

> ⚠️ **Warning**: This project is under active development. While functional, some features may still require refinement.

## Overview

SABER is a tool for monitoring Pulsar endpoint reliability across Galaxy instances. It was developed to meet the practical challenges of managing distributed computing resources.

It provides: 
* Workflow-based testing to simulate real usage conditions
* Encrypted configuration management
* HTML, Markdown, and summary tables reports
* Detailed logging with syslog integration

## Installation

To install in development mode, clone this repository and navigate to the corresponding directory, then run:

```bash
python3 -m venv venv
. ./venv/bin/activate
pip install -e .
```

## Quick Start

```bash
# Generate example configuration file
saber -x > ~/.config/saber/settings.yaml

# Edit the configuration with encryption
saber -e ~/.config/saber/settings.yaml -p /path_to/password.txt
# Alternative: set the SABER_PASSWORD environment variable

# Run tests and generate an HTML report
saber -r ~/my_saber_report.html -p /path_to/password.txt

# Alternative: output JSON to stdout
saber -j -p /path_to/password.txt
```

## Usage

SABER uses a command-line interface.

### Basic Structure

```bash
saber [-h] [-p PASSWORD] [-j] [-r [PATH]] [-m [PATH]] [-t [PATH]] [-l LOG_DIRECTORY] [-e PATH | -c PATH | -d PATH | -s PATH | -x]
```

### Common Options

* **-p, --password**: Required for encrypted configuration operations
* **-r, --html\_report**: Generates an HTML report (`~/saber_report_TIMESTAMP.html` by default)
* **-m, --md\_report**: Generates a Markdown report
* **-t, --table\_html\_report**: Generates a summarized HTML table
* **-j, --print\_json**: Prints results in JSON format to stdout
* **-l, --log\_dir**: Specifies log directory (default locations vary by privilege)
* **-e, --edit**: Opens encrypted settings in `$EDITOR` (fallbacks to `nano`); re-encrypts on save
* **-c, --encrypt**/**-d, --decrypt**: Encrypt or decrypt files
* **-s, --settings**: Specify an alternate settings file
* **-x, --example\_settings**: Output example configuration

## Configuration

* **Location**: `~/.config/saber/settings.yaml` or overridden with `-s`
* **Structure**: Supports hierarchical settings; instance-specific parameters override global defaults
* **Key Parameters**:

  * `maxwait`: Upload/execution completion timeout
  * `timeout`: General operation timeout
  * `interval`: Delay between upload status checks
  * `sleep_time`: Delay between job monitoring checks
* **Workflow Requirement**: Workflow files (`.ga`) must be specified in the settings file

## Logging

* **Default locations**:

  * Root: `/var/log/saber/saber.log` (not recommended)
  * User: `~/.local/state/saber/log/saber.log`
* **Forwarded to**: syslog
* **Format**:

```
YYYY-MM-DD HH:MM:SS LEVEL [galaxy@endpoint] Message
```

Example:

```
2025-02-14 15:12:31,070 INFO [usegalaxy@TBD] Updating pulsar endpoint in user preferences
2025-02-14 15:12:31,210 INFO [usegalaxy@Default] Testing pulsar endpoint Default from usegalaxy instance
2025-02-14 15:13:14,173 INFO [usegalaxy@example] Testing pulsar endpoint example from usegalaxy instance
```

The bracketed information identifies the Galaxy server and associated Pulsar endpoint being tested. `TBD` indicates Galaxy instance initialization phases, while `Default` represents the local compute endpoint utilized during dataset upload operations.

## Development Status

Active development. Priorities:

* Template optimization
* Error handling refinement
