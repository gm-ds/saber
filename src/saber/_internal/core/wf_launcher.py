#!/usr/bin/env python3

"""Workflow testing launcher for Galaxy instances."""

from typing import Union

from saber.biolog import LoggerLike, WFPathError, WFInvocation

from saber._internal.utils.globals import ERR_CODES

from saber.biolog import GalaxyTest


def _wf_launcher(config: dict, Logger: LoggerLike) -> Union[int, list]:
    """Launch and monitor workflow tests across multiple Galaxy instances and compute endpoints.

    This function iterates through configured Galaxy instances, sets up test workflows
    for each instance, executes tests across all specified compute endpoints, monitors
    job execution and collects results, and handles cleanup and error conditions.

    Args:
        config (dict): Dictionary containing test configuration with the following keys:
            - usegalaxy_instances: List of Galaxy instance configurations
            - endpoints: List of compute endpoints to test
            - Other configuration parameters
        Logger (LoggerLike): Logger instance for output and error reporting.

    Returns:
        Union[int, list]: Test execution result in one of two formats:
            - int: Returns 0 on complete success
            - list: Returns [error_code, partial_results] on partial success/failure
                where error_code is one of:
                    - ERR_CODES["path"]: System exit occurred
                    - ERR_CODES["api"]: Galaxy API error occurred
                    - ERR_CODES["jobs"]: Jobs failed
                    - ERR_CODES["gal"]: Galaxy-specific errors
                and partial_results is a nested dictionary with structure:
                    {
                        "instance_name": {
                            "compute_endpoint": {
                                "SUCCESSFUL_JOBS": {
                                    "job_id": {
                                        "INFO": {
                                            "tool_id": str,
                                            "state": str,
                                            "inputs": dict,
                                            "outputs": dict
                                        },
                                        "METRICS": [
                                            {
                                                "title": str,
                                                "value": str,
                                                "plugin": str
                                            }
                                        ]
                                    }
                                },
                                "FAILED_JOBS": {
                                    "job_id": {
                                        "INFO": {
                                            "tool_id": str,
                                            "state": str,
                                            "exit_code": int
                                        },
                                        "PROBLEMS": {
                                            "has_empty_inputs": bool,
                                            "has_duplicate_inputs": bool
                                        }
                                    }
                                },
                                "QUEUED_JOBS": {
                                    "job_id": {
                                        "INFO": {
                                            "tool_id": str,
                                            "state": str
                                        }
                                    }
                                }
                            }
                        }
                    }

    Raises:
        WFPathError: If workflow files are not accessible.
        KeyboardInterrupt: If user interrupts execution.
        ConnectionError: If connection errors occur with usegalaxy.* instances.
        Exception: For other unexpected errors during execution.

    """
    results = dict()
    conn_rr = False
    exc = False
    try:
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

            except WFPathError as e:
                Logger.error(e)
                Logger.warning(f"Exiting with error: {ERR_CODES['path']}")
                galaxy_instance.clean_up()
                return ERR_CODES["path"]
            except Exception as e:
                exc = True
                Logger.warning(f"Error: {e}")
                galaxy_instance.clean_up()
                if not i == len(config["usegalaxy_instances"]) - 1:
                    Logger.warning("Skipping to the next instance")
                continue
            except ConnectionError as e:
                conn_rr = True
                Logger.warning(f"Connection Error while testing {useg['name']}:")
                Logger.warning(f"{e}")
                galaxy_instance.clean_up()
                if not i == len(config["usegalaxy_instances"]) - 1:
                    Logger.warning("Skipping to the next instance")
                continue

            try:
                partial = dict()
                partial = galaxy_instance.execute_and_monitor_workflow(
                    workflow_input=input
                )

                results = partial | results

            except Exception as e:
                Logger.warning(
                    f"An error occurred while testing: {galaxy_instance.p_endpoint}"
                )
                Logger.warning(f"Error: {e}")
                Logger.warning("Continuing...")
                continue

            except WFInvocation as e:
                Logger.warning(
                    f"An error occurred while invoking the workflow for {galaxy_instance.p_endpoint}"
                )
                Logger.warning(f"Error: {e}")
                Logger.warning("Continuing...")
                continue

            except ConnectionError as e:
                Logger.warning(
                    f"A Connection error occurred while testing: {galaxy_instance.p_endpoint}"
                )
                Logger.warning(f"{e}")
                Logger.warning("Continuing...")
                continue

            try:
                galaxy_instance.clean_up()
                galaxy_instance.switch_pulsar(original_prefs=True)

            except Exception as e:
                Logger.warning("An error occurred while cleaning up:")
                Logger.warning(f"{e}")
                Logger.warning("Continuing...")

            except ConnectionError as e:
                Logger.warning("An error occurred while cleaning up:")
                Logger.warning(f"{e}")
                Logger.warning("Continuing...")

        Logger.info("Test completed")

        for g_name, g_data in results.items():
            for com_id, job_data in g_data.items():
                for k in [
                    "RUNNING_JOBS",
                    "WAITING_JOBS",
                    "QUEUED_JOBS",
                    "NEW_JOBS",
                ]:
                    if job_data.get(k):
                        Logger.warning(f"Uncompleted jobs found in {g_name}/{com_id}.")
                        Logger.warning(f"Exiting with code: {ERR_CODES['tto']}")
                        if not conn_rr or not exc:
                            return [ERR_CODES["tto"], results]
                if job_data.get("FAILED_JOBS"):
                    Logger.warning(f"Failed jobs found in {g_name}/{com_id}.")
                    Logger.warning(f"Exiting with code: {ERR_CODES['job']}")
                    if not conn_rr or not exc:
                        return [ERR_CODES["job"], results]
        if conn_rr:
            return [ERR_CODES["api"], results]
        if exc:
            return [ERR_CODES["gal"], results]

        return [0, results]

    except KeyboardInterrupt:
        Logger.warning("Test interrupted")
        galaxy_instance.clean_up()
        print("\n")
        raise
