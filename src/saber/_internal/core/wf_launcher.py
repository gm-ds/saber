#!/usr/bin/env python3

"""Workflow testing launcher for Galaxy instances."""

from typing import Union

from saber.biolog import LoggerLike


def _wf_launcher(config: dict, Logger: LoggerLike) -> Union[int, list]:
    """Launch and monitor workflow tests across multiple Galaxy instances and compute endpoints.

        This function:
        1. Iterates through configured Galaxy instances
        2. Sets up test workflows for each instance
        3. Executes tests across all specified compute endpoints
        4. Monitors job execution and collects results
        5. Handles cleanup and error conditions

        Args:
            config: Dictionary containing test configuration with:
                - usegalaxy_instances: List of Galaxy instance configurations
                - endpoints: List of compute endpoints to test
                - Other parameters
            Logger: Logger instance for output and error reporting

        Returns:
            Union[int, list]: Returns one of:
                - [0, results] on complete success
                - [error_code, partial_results] on partial success/failure
                - 0 on keyboard interrupt (clean exit)
            Where error_code can be:
                - PATH_EXIT: System exit occurred
                - GAL_ERROR: Galaxy API error occurred
                - TIMEOUT_EXIT: Jobs/SABER timed out
                - JOB_ERR_EXIT: Jobs failed
            And results is a nested dictionary structure containing:
                {
        "instance_1": {
            "compute_1": {
                "SUCCESSFUL_JOBS": {
                    "job_id_1": {
                        "INFO": {
                            "tool_id": "tool_namespace/tool_name/tool_version",
                            "state": "ok",
                            "inputs": {
                                "input_name": {"id": "dataset_id", "src": "hda", "uuid": "dataset_uuid"}
                            },
                            "outputs": {
                                "output_name": {"id": "dataset_id", "src": "hda", "uuid": "dataset_uuid"}
                            }
                        },
                        "METRICS": [
                            {
                                "title": "Metric Name",
                                "value": "Metric Value",
                                "plugin": "source"
                            }
                        ]
                    }
                },
                "FAILED_JOBS": {
                    "job_id_2": {
                        "INFO": {
                            "tool_id": "tool_namespace/tool_name/tool_version",
                            "state": "error",
                            "exit_code": 1
                        },
                        "PROBLEMS": {
                            "has_empty_inputs": false,
                            "has_duplicate_inputs": false
                        }
                    }
                },
                "QUEUED_JOBS": {
                    "job_id_3": {
                        "INFO": {
                            "tool_id": "tool_namespace/tool_name/tool_version",
                            "state": "queued"
                        }
                    }
                }
            },
            "compute_2": {
                # Similar structure as compute_1
            }
        },
        "instance_2": {
            # Similar structure as instance_1
        }
    }

        Raises:
            SystemExit: If critical error occurs during execution
            KeyboardInterrupt: If user interrupts execution
            Exception: For other unexpected errors during execution
    """
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
            Logger.error(f"Workflow PAth error: {e}")
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
