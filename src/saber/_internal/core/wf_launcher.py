#!/usr/bin/env python3

from argparse import Namespace

from saber.biolog import LoggerLike


def _job_launcher(Parsed_Args: Namespace, Logger: LoggerLike) -> int:
    from saber._internal.cli import _init_config, _reports_helper
    from saber._internal.commands import (
        _html_report,
        _md_report,
        _print_json,
        _table_html_report,
    )
    from saber._internal.utils.globals import (
        GAL_ERROR,
        JOB_ERR_EXIT,
        PATH_EXIT,
        TIMEOUT_EXIT,
    )
    from saber.biolog import GalaxyTest

    config = _init_config(Logger, Parsed_Args)
    if not isinstance(config, dict):
        return config

    config = _reports_helper(Parsed_Args, config)

    results = dict()

    for i in range(len(config["usegalaxy_instances"])):

        useg = dict(config["usegalaxy_instances"][i])
        copyconf = config.copy()
        copyconf.pop("usegalaxy_instances", None)
        copyconf.update(useg)
        useg = copyconf

        galaxy_instance = GalaxyTest(
            useg["url"],
            useg["api"],
            useg.get("email", None),
            useg.get("password", None),
            useg,
            Logger,
        )

        try:
            try:
                input = galaxy_instance.test_job_set_up()
            except SystemExit as e:
                Logger.error(f"Program exiting with code {e}")
                return PATH_EXIT

            for pe in useg["endpoints"]:
                galaxy_instance.switch_pulsar(pe)
                compute_id = pe if pe != "None" else "Default"

                if useg["name"] not in results:
                    results[useg["name"]] = {}

                if compute_id not in results[useg["name"]]:
                    results[useg["name"]][compute_id] = {
                        "SUCCESSFUL_JOBS": {},
                        "TIMEOUT_JOBS": {},
                        "FAILED_JOBS": {},
                    }

                pre_results = galaxy_instance.execute_and_monitor_workflow(
                    workflow_input=input
                )
                for key in ["SUCCESSFUL_JOBS", "TIMEOUT_JOBS", "FAILED_JOBS"]:
                    if key in pre_results and isinstance(pre_results[key], dict):
                        results[useg["name"]][compute_id][key].update(pre_results[key])

            Logger.info("Cleaning Up...")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow()
            galaxy_instance.switch_pulsar(useg["default_compute_id"])
            Logger.info("Test completed")

        except KeyboardInterrupt:
            Logger.warning("Test interrupted")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow()
            Logger.info("Clean-up terminated")
            print("\n")
            return 0

        except Exception as e:
            Logger.warning(f"Error: {e}")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow()
            Logger.info("Clean-up terminated")
            if i == len(config["usegalaxy_instances"]) - 1:
                Logger.warning("Exiting with error")
                return GAL_ERROR
            Logger.warning("Skipping to the next instance")

    _html_report(Parsed_Args, results, config)

    _md_report(Parsed_Args, results, config)

    _table_html_report(Parsed_Args, results, config)

    _print_json(Parsed_Args, results)

    for g_name, g_data in results.items():
        for com_id, job_data in g_data.items():
            if job_data.get("TIMEOUT_JOBS"):
                Logger.warning(f"Timeout jobs found in {g_name}/{com_id}.")
                Logger.warning(f"Exiting with code: {TIMEOUT_EXIT}")
                return TIMEOUT_EXIT
            if job_data.get("FAILED_JOBS"):
                Logger.warning(f"Failed jobs found in {g_name}/{com_id}.")
                Logger.warning(f"Exiting with code: {JOB_ERR_EXIT}")
                return JOB_ERR_EXIT
    return 0
