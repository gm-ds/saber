#!/usr/bin/env python3

from typing import Union

from saber.biolog import LoggerLike


def _wf_launcher(config: dict, Logger: LoggerLike) -> Union[int, list]:

    from saber._internal.utils.globals import (
        GAL_ERROR,
        JOB_ERR_EXIT,
        PATH_EXIT,
        TIMEOUT_EXIT,
    )
    from saber.biolog import GalaxyTest

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
            input = galaxy_instance.test_job_set_up()

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

        except SystemExit as e:
            Logger.error(f"Program exiting with code: {e}")
            if i == len(config["usegalaxy_instances"]) - 1:
                Logger.warning("Exiting with error")
                return [PATH_EXIT, results]
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
                return [GAL_ERROR, results]
            Logger.warning("Skipping to the next instance")

    for g_name, g_data in results.items():
        for com_id, job_data in g_data.items():
            if job_data.get("TIMEOUT_JOBS"):
                Logger.warning(f"Timeout jobs found in {g_name}/{com_id}.")
                Logger.warning(f"Exiting with code: {TIMEOUT_EXIT}")
                return [TIMEOUT_EXIT, results]
            if job_data.get("FAILED_JOBS"):
                Logger.warning(f"Failed jobs found in {g_name}/{com_id}.")
                Logger.warning(f"Exiting with code: {JOB_ERR_EXIT}")
                return [JOB_ERR_EXIT, results]
    return [0, results]
