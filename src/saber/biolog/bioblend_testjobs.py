#!/usr/bin/env python3

import re
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from bioblend import ConnectionError
from bioblend.galaxy import GalaxyInstance, datasets
from bioblend.galaxy.histories import HistoryClient

from saber.biolog.loglike import LoggerLike
from saber.biolog.logger import CustomLogger


class GalaxyTest:
    """Creates a GalaxyInstance using bioblend, and logs operations with a custom logger.

    Both API and mail/password are supported. Sets some defaults if not present in the dict passed
    for initialization.

    Args:
        url (str): API key of a usegalaxy instance, has precedence over mail and password
        email (str, optional): To be used along the password of the account
        gpassword (str, optional): To be used along the email of the account
        config (dict, optional): Dictionary containing everything needed for the test jobs excluding the workflow
        class_logger (Any, optional): Logger instance used by the class.

    """

    def __init__(
        self,
        url: str,
        key: str,
        email: str = None,
        gpassword: str = None,
        config: dict = None,
        Logger: LoggerLike = None,
    ) -> None:
        """Initializes a bioblend Galaxy instance and sets up configuration for job management.

        Args:
            url (str): The URL of the Galaxy server.
            key (str): The API key for Galaxy authentication (used if email and gpassword are not provided).
            email (str, optional): The email address for Galaxy authentication. Defaults to None.
            gpassword (str, optional): The password for Galaxy authentication. Defaults to None.
            config (dict, optional): User-defined configuration options to override defaults. Defaults to None.
            Logger (LoggerLike, optional): Logger instance for logging messages. Defaults to None.

        Attributes:
            logger: Logger instance for logging.
            gi: GalaxyInstance object for interacting with the Galaxy server.
            p_endpoint (str): Placeholder for endpoint information.
            err_tracker (bool): Error tracking flag.
            config (dict): Merged configuration dictionary.
            current_date (str): Current date and time string for history naming.
            history_client (HistoryClient): Client for managing Galaxy histories.
            history: Placeholder for the current Galaxy history.
            wf: Placeholder for the current workflow.

        Returns:
            None

        Raises:
            None
        """
        # Initialize GalaxyInstance
        self.logger = Logger
        self.p_endpoint = ""
        self.err_tracker = False
        self.tagged_jobs = {}

        # Default configuration
        default_config = {
            "sleep_time": 5,
            "maxwait": 12000,
            "interval": 5,
            "timeout": 12000,
            "history_name": "SABER",
            "clean_history": "onsuccess",
        }
        # Merge user-defined config with defaults
        self.config = {**default_config, **(config or {})}
        self.pe_list = list(self.config["endpoints"])
        self.current_date = datetime.now().strftime("%-d/%-m/%y %H:%M")
        self.config["history_name"] = (
            f"{self.config.get('history_name', 'SABER')} {self.current_date}"
        )
        self.gi = (
            GalaxyInstance(url, email, gpassword)
            if ((email is not None) and (gpassword is not None))
            else GalaxyInstance(url, key)
        )
        self.user = self.gi.users.get_current_user()
        self._update_log_context()
        self.logger.info("useGalaxy connection initialized")
        self.history_client = HistoryClient(self.gi)
        self.history = None
        self.wf = None
        self.invocation_ids = {}
        for pe in self.pe_list:
            if pe == "None":
                pe = "Default"
            self.tagged_jobs[pe] = []

    def _update_log_context(self, endpoint: str = None, name: str = None) -> None:
        """Update the logging context with Galaxy instance and endpoint information.

        This method updates the contextual information that gets injected into
        all subsequent log messages if the logger is an instance of Custom Logger.
        The context includes the Galaxy instance
        name and associated endpoint, which helps track log messages across
        different test environments.

        Args:
            name (str, optional): Name of the Galaxy instance being
                used for logging context. Defaults to "None".
            endpoint (str, optional): Endpoint associated with the Galaxy
                instance at that moment (e.g., Pulsar endpoint). Defaults to "Default".

        Returns:
            None

        """
        name = self.config.get("name", "None") if name is None else name
        if endpoint == "None" or endpoint is None:
            endpoint = "Default"
        self.p_endpoint = endpoint
        if isinstance(self.logger, CustomLogger):
            self.logger.update_log_context(instance_name=name, endpoint=endpoint)

    def test_job_set_up(
        self,
        inputs_data: dict = None,
        maxwait: int = None,
        interval: int = None,
        local: bool = None,
    ) -> dict:
        """Sets up new histories and upload workflows.

        Args:
            inputs_data (dict, optional): Dictionary with the inputs for the workflow
            maxwait (int, optional): Maximum wait, in seconds, during upload of the datasets. Defaults to 12000
            interval (int, optional): Interval between status checks, defaults to 5s.
            local (bool, optional): Defaults to True. When False it will not change the User
                Preferences, possibly trying to upload the datasets through a Pulsar Endpoint.

        Returns:
            dict: Dictionary containing the workflow inputs

        """
        inputs_data = self.config["data_inputs"] if inputs_data is None else inputs_data
        interval = self.config["interval"] if interval is None else interval
        maxwait = self.config["maxwait"] if maxwait is None else maxwait
        local = self.config.get("local_upload", True) if local is None else local

        if local:
            self.switch_pulsar(
                self.config["default_compute_id"], name=self.config["name"]
            )
        self._create_history()
        self._upload_workflow()
        inputs_dict = inputs_data
        data = dict()
        self.logger.info("Uploading and building Datasets")
        for file_name, file_options in inputs_dict.items():
            file_url = file_options["url"]
            file_type = file_options["file_type"]
            upload = self.gi.tools.put_url(
                file_url,
                history_id=self.history["id"],
                file_name=file_name,
                file_type=file_type,
            )
            upload_id = upload["outputs"][0]["id"]
            wf_input = self.gi.workflows.get_workflow_inputs(
                self.wf["id"], label=file_name
            )[0]
            data[wf_input] = {"id": upload_id, "src": "hda"}

        # Wait for dataset
        self.logger.info("Waiting for datasets...")
        self._wait_for_dataset(maxwait, interval)

        return data

    def _wait_for_dataset(self, maxtime: int = None, interval: int = 5) -> bool:
        """Wait for dataset upload.

        Args:
            maxtime (int, optional): Maximum time to wait. Defaults to config value.
            interval (int, optional): Interval between checks. Defaults to 5.

        Returns:
            bool: True if datasets are ready, False if timeout occurred

        """
        maxtime = self.config["maxwait"] if maxtime is None else maxtime
        dataset_client = datasets.DatasetClient(self.gi)
        all_datasets = dataset_client.get_datasets(history_id=self.history["id"])

        def check_dataset_ready() -> bool:
            """Check if datasets are ready for processing.

            Returns:
                bool: True if all datasets are in terminal state, False otherwise.
            """
            for dataset in all_datasets:
                dataset_id = dataset["id"]

                dataset_info = dataset_client.show_dataset(dataset_id)
                state = dataset_info["state"]

                if state in {"ok", "empty", "error", "discarded", "failed_metadata"}:
                    if state != "ok":
                        self.logger.warning(
                            f"Dataset {dataset_id} is in terminal state {state}"
                        )
                        self.logger.error(f"Upload of Dataset {dataset_id} failed")
                        return True
                    if state in {"ok", "empty"}:
                        continue
                self.logger.info(
                    f"Dataset {dataset_id} is in non-terminal state {state}"
                )

                return False
            return True

        return self._wait_for_state(
            check_dataset_ready, maxtime, interval, "Upload time exceeded"
        )

    def _create_history(self, history_name: str = None) -> None:
        """Create a new History.

        Deletes permanently older histories (>1 week) to ensure enough space.

        Args:
            history_name (str, optional): Defaults to "Pulsar Endpoints Test"

        """
        if history_name is None:
            history_name = self.config.get("history_name", f"SABER {self.current_date}")
        # Delete older histories to ensure there's enough free space
        self.purge_histories()

        self.logger.info("Creating History...")
        self.history = self.history_client.create_history(name=history_name)
        self.logger.info(f"         History ID: {self.history['id']}")

    def _safe_delete_history(self, id: str, purge_bool: bool) -> None:
        """Safely delete a history, handling immutable histories.

        Args:
            id (str): History ID to delete
            purge_bool (bool): Whether to purge the history

        """
        try:
            self.history_client.delete_history(history_id=id, purge=purge_bool)
        except ConnectionError as e:
            if "403003" in str(e):
                self.logger.warning(f"Skipping immutable history: {id}")
                return
            raise

    @staticmethod
    def _clean_string(s: str) -> str:
        """Clean a string by removing numbers and slashes, and converting to lowercase.

        Args:
            s (str): Input string to clean

        Returns:
            str: Cleaned string with numbers/slashes removed and in lowercase

        """
        s = re.sub(r"[0-9/:]", "", s)
        s = s.lower()
        return s.strip()

    def purge_histories(self, purge_new: bool = True, purge_old: bool = True) -> None:
        """Purge histories with the same names used during tests or older than 1 week.

        Args:
            purge_new (bool, optional): Defaults True - purges all histories with test name
            purge_old (bool, optional): Defaults True - purges ALL histories older than one week

        """
        if self.history_client is not None:
            for history in self.history_client.get_histories():
                if self.config.get("history_name") == history["name"] and purge_new:
                    self.logger.info(
                        f"Purging History, ID: {history['id']}, Name: {history['name']}"
                    )
                    self._safe_delete_history(history["id"], purge_bool=True)
                create_time = self.history_client.show_history(
                    history_id=history["id"], keys=["create_time"]
                )
                if (
                    datetime.today()
                    - datetime.strptime(
                        create_time["create_time"], "%Y-%m-%dT%H:%M:%S.%f"
                    )
                ) > timedelta(
                    hours=36
                ) and purge_old:  # TODO: add retention time to yaml config
                    config_clean = self._clean_string(self.config.get("history_name"))
                    history_clean = self._clean_string(history.get("name"))
                    if config_clean in history_clean:
                        self.logger.info(
                            f"Purging History, ID: {history['id']}, Name: {history['name']}"
                        )
                        self._safe_delete_history(history["id"], purge_bool=True)
                        return
                    history_words = history_clean.split()
                    for word in history_words:
                        if config_clean == word:
                            self.logger.info(
                                f"Purging History, ID: {history['id']}, Name: {history['name']}"
                            )
                            self._safe_delete_history(history["id"], purge_bool=True)
                            return

    def _upload_workflow(self, wf_path: str = None) -> None:
        """Upload Workflow file to usegalaxy.* instance.

        Args:
            wf_path (str, optional): Path to the workflow file. Defaults to config value.

        Raises:
            WFPathError: If no workflow path is provided or path doesn't exist

        """
        wf_path = self.config.get("ga_path", None) if wf_path is None else wf_path
        if wf_path is None:
            error_msg = "No workflow path provided in config file."
            raise WFPathError(error_msg)

        wf_path = Path(wf_path).expanduser()

        if not wf_path.is_absolute():
            config_path = self.config.get("config_path", None)
            if config_path:
                c_wf_path = Path(config_path).parent / wf_path
                c_wf_path = c_wf_path.resolve()
                if c_wf_path.exists():
                    wf_path = c_wf_path
                else:
                    wd_wf_path = Path.cwd() / wf_path  # Fall back to CWD
                    wd_wf_path = wd_wf_path.resolve()
                    if wd_wf_path.exists():
                        wf_path = wd_wf_path
            else:
                wd_path = Path.cwd() / wf_path  # Fall back to CWD
                wd_path = wd_path.resolve()
                if wd_path.exists():
                    wf_path = wd_path

        if wf_path.exists():
            self.logger.info(f"Uploading Workflow, local path: {wf_path}")
            self.wf = self.gi.workflows.import_workflow_from_local_path(str(wf_path))
        else:
            error_msg = f"Workflow path does not exist: {wf_path}"
            raise WFPathError(error_msg)

    def purge_workflow(self) -> None:
        """Delete permanently the workflow uploaded for the test."""
        if self.wf is not None:
            self.gi.workflows.delete_workflow(self.wf["id"])
            self.logger.info(f"Purging Workflow, ID: {self.wf['id']}")

    @staticmethod
    def _tool_id_split(tool_id: str) -> str:
        """Remove characters before "/devteam" inclusively to avoid log clutter.

        Args:
            tool_id (str): Original tool ID

        Returns:
            str: Cleaned tool ID

        """
        if "/devteam/" in tool_id:
            return tool_id.split("/devteam/")[1]
        else:
            return tool_id

    def _monitor_job_status(
        self, timeout: int = None, sleep_time: int = None, wait_for_inv: str = None
    ) -> dict:
        """Monitor the status of a job invocation.

        Args:
            invocation_id (str): The ID of the workflow invocation to monitor
            timeout (int, optional): Maximum time (in seconds) to wait. Defaults to 12000s. It is halfed for initial job start.
            sleep_time (int, optional): Time between status checks. Defaults to 5s
            wait_for_inv (str, optional): If not None, waits for all jobs to start before checking completion. Defaults to None.

        Returns:
            None

        """
        sleep_time = self.config["sleep_time"] if sleep_time is None else sleep_time
        timeout = self.config["timeout"] if timeout is None else timeout
        pe_list = self.pe_list.copy()
        terminal_state_job: list[str] = []

        def all_jobs_started() -> bool:
            """Check if all jobs in the invocation have progressed beyond initial states.

            Returns:
                bool: True if all jobs have states different from empty string or "new", False otherwise.
            """
            pe = wait_for_inv
            self._update_log_context(endpoint=pe)

            # Get job status
            jobs = self.gi.jobs.get_jobs(invocation_id=self.invocation_ids.get(pe, ""))
            if not jobs:
                return False

            all_jobs_started = True
            for i in range(len(jobs)):
                current_job = jobs[i]
                self._add_tag(current_job["id"])
                job_state = current_job["state"]
                tool_id = self._tool_id_split(current_job.get("tool_id"))
                self.logger.info(f"    {job_state}    Tool ID: {tool_id}")

                # Continue monitoring
                if job_state not in ["ok", "error", "running", "queued", "waiting"]:
                    all_jobs_started = False

            return all_jobs_started

        def job_completed() -> bool:
            """Check if all jobs in multiple invocation have completed.

            Returns:
                bool: True if all jobs are completed, False otherwise.
            """
            all_jobs_completed = True  # N.B.:Needs to be outside the outer loop or it will give false negatives
            for pe in pe_list.copy():
                self._update_log_context(endpoint=pe)

                # Get job status
                jobs = self.gi.jobs.get_jobs(
                    invocation_id=self.invocation_ids.get(pe, "")
                )
                if not jobs:
                    return False

                one_inv_completed = True
                for i in range(len(jobs)):
                    current_job = jobs[i]
                    job_state = current_job["state"]
                    if current_job["id"] not in terminal_state_job:
                        tool_id = self._tool_id_split(current_job.get("tool_id"))
                        self.logger.info(f"    {job_state}    Tool ID: {tool_id}")
                        self._add_tag(current_job["id"])
                    if job_state in ["ok", "error"]:
                        terminal_state_job.append(current_job["id"])
                    # Continue monitoring
                    if job_state not in ["ok", "error"]:
                        one_inv_completed = False
                        all_jobs_completed = False

                if one_inv_completed:
                    pe_list.remove(pe)

            return all_jobs_completed

        if wait_for_inv is not None:
            self.logger.info(
                "Waiting until test jobs start before invoking additional ones. Current state:"
            )
            timeout = min(600, timeout)  # Reduce timeout for initial job start
            sleep_time = min(sleep_time, 5)
            self._wait_for_state(
                all_jobs_started,
                timeout,
                sleep_time,
                f"Not all jobs started in {timeout}s.",
            )
        else:
            self.logger.info("Waiting until test jobs finish. Current states:")
            self._wait_for_state(
                job_completed, timeout, sleep_time, f"Timeout {timeout}s expired."
            )

    def _handle_job_completion(
        self
    ) -> dict[dict[dict[list[dict[str, any]]]]]:
        """Job completion handler. Changes History name in case of failures.

        Args:
            jobs (list[dict[str, any]]): List of job dictionaries

        Returns:
            dict: Dictionary containing successful, timeout and failed jobs with their details

        """
        return_values = {}
        if self.config["name"] not in return_values:
            return_values[self.config["name"]] = {}
        for pe in self.pe_list:
            self._update_log_context(endpoint=pe)
            compute_id = pe if pe != "None" else "Default"

            if compute_id not in return_values[self.config["name"]]:
                return_values[self.config["name"]][compute_id] = {}
                for key in [
                    "SUCCESSFUL_JOBS",
                    "RUNNING_JOBS",
                    "QUEUED_JOBS",
                    "NEW_JOBS",
                    "WAITING_JOBS",
                    "FAILED_JOBS",
                ]:
                    return_values[self.config["name"]][compute_id][key] = {}


            if self.invocation_ids.get(pe) in self.invocation_ids.values():
                jobs = self.gi.jobs.get_jobs(invocation_id=self.invocation_ids[pe])


            for job in jobs:
                if job:
                    if job["state"] in ["new", "queued", "running", "waiting"]:
                        self.logger.info(f"Job {job['id']} reached tool timeout:")
                        self.logger.info(
                            f"         Tool: {self._tool_id_split(job['tool_id'])} Status: {job['state']}"
                        )
                        self._add_tag(job["id"], msg_list=f"saber_{job['state']}")
                        self.err_tracker = True
                        if job["state"] == "running":
                            return_values[self.config["name"]][compute_id][
                                "RUNNING_JOBS"
                            ][job["id"]] = {
                                "INFO": self.gi.jobs.show_job(job["id"]),
                                "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                                "METRICS": self.gi.jobs.get_metrics(job["id"]),
                            }
                        if job["state"] == "new":
                            return_values[self.config["name"]][compute_id]["NEW_JOBS"][
                                job["id"]
                            ] = {
                                "INFO": self.gi.jobs.show_job(job["id"]),
                                "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                                "METRICS": self.gi.jobs.get_metrics(job["id"]),
                            }
                        if job["state"] == "queued":
                            return_values[self.config["name"]][compute_id][
                                "QUEUED_JOBS"
                            ][job["id"]] = {
                                "INFO": self.gi.jobs.show_job(job["id"]),
                                "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                                "METRICS": self.gi.jobs.get_metrics(job["id"]),
                            }
                        if job["state"] == "waiting":
                            return_values[self.config["name"]][compute_id][
                                "WAITING_JOBS"
                            ][job["id"]] = {
                                "INFO": self.gi.jobs.show_job(job["id"]),
                                "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                                "METRICS": self.gi.jobs.get_metrics(job["id"]),
                            }

                    # Handle completion
                    elif job["exit_code"] == 0 or job["state"] == "ok":
                        self.logger.info(f"Job {job['id']} succeeded:")
                        self.logger.info(
                            f"         Tool: {self._tool_id_split(job['tool_id'])}"
                        )
                        return_values[self.config["name"]][compute_id][
                            "SUCCESSFUL_JOBS"
                        ][job["id"]] = {
                            "INFO": self.gi.jobs.show_job(job["id"]),
                            "METRICS": self.gi.jobs.get_metrics(job["id"]),
                        }
                        if (
                            self.config.get("clean_history", "onsuccess")
                            == "successful_only"
                        ):
                            self._delete_job_out(job["id"])
                        else:
                            self._add_tag(job["id"])

                    else:
                        # Handle failure
                        job_exit_code = (
                            job["exit_code"]
                            if job and job["exit_code"] is not None
                            else "None"
                        )
                        self.logger.info(
                            f"Job {job['id']} failed (exit_code: {job_exit_code}):"
                        )
                        self.logger.info(
                            f"         Tool: {self._tool_id_split(job['tool_id'])}"
                        )
                        return_values[self.config["name"]][compute_id]["FAILED_JOBS"][
                            job["id"]
                        ] = {
                            "INFO": self.gi.jobs.show_job(job["id"]),
                            "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                            "METRICS": self.gi.jobs.get_metrics(job["id"]),
                        }
                        self._add_tag(job["id"], msg_list="err")
                        self.err_tracker = True
        return return_values

    def execute_and_monitor_workflow(
        self, workflow_input: dict, timeout: int = None
    ) -> dict[list[dict[str, any]]]:
        """Executes a workflow and monitors its status until completion or timeout.

        Args:
            workflow_input (dict): Input parameters for the workflow
            timeout (int, optional): Maximum time to wait (in seconds). Defaults to 12000s

        Returns:
            dict: Dictionary containing job status information

        """
        timeout = self.config["timeout"] if timeout is None else timeout
        for pe in self.pe_list:
            self.switch_pulsar(pe)

            try:
                # Workflow invocation
                invocation = self.gi.workflows.invoke_workflow(
                    self.wf["id"], inputs=workflow_input, history_id=self.history["id"]
                )
            except WFInvocation as e:
                self.logger.warning(f"Error invoking workflow for {pe}.")
                self.logger.error(f"Error: {e}")
                continue
            except ConnectionError as e:
                self.logger.warning(f"Connection Error invoking workflow for {pe}: {e}")
                self.logger.error(f"Connection Error: {e}")
                continue

            self.invocation_ids[pe] = invocation["id"]
            self.logger.info(f"Invocation id: {self.invocation_ids[pe]}")
            self._monitor_job_status(wait_for_inv=pe)

        # Monitor the job using the previous function!
        self._monitor_job_status()

        # Handle job completion
        return self._handle_job_completion()

    def switch_pulsar(
        self, p_endpoint: str = None, name: str = None, original_prefs: bool = False
    ) -> None:
        """Switches to a different Pulsar endpoint for processing.

        Args:
            p_endpoint (str, Optional): The Pulsar endpoint to switch to, defaults to default_compute_id in config.
            name (str, optional): Name for the Pulsar instance. Defaults to config value
            original_prefs (bool, optional): If True, restores preferences. Defaults to False.

        """
        name = self.config["name"] if name is None else name
        p_endpoint = self.config["default_compute_id"] if p_endpoint is None else p_endpoint
        prefs = self.user.get("preferences", {}).copy()
        extra_prefs = prefs.get("extra_user_preferences", "{}")
        new_prefs = json.loads(extra_prefs).copy()

        if not original_prefs:
            # TODO: find a workaround to not use the json library only for this bit
            new_prefs.update({"distributed_compute|remote_resources": p_endpoint})
        else:
            new_prefs = json.loads(extra_prefs).copy()

        if prefs != new_prefs:
            self.logger.info("Updating pulsar endpoint in user preferences")
            self.gi.users.update_user(user_id=self.user["id"], user_data=new_prefs)
            p_endpoint = new_prefs.get("distributed_compute|remote_resources") if original_prefs else p_endpoint
            self._update_log_context(endpoint=p_endpoint)
            self.logger.info(
                f"Switching to pulsar endpoint {p_endpoint} from {name} instance"
            )

    def _wait_for_state(
        self,
        check_function: Callable[[], bool],
        timeout: int,
        interval: int,
        error_msg: str,
    ) -> bool | None:
        """Waits for a specific state to be reached by periodically checking.

        Args:
            check_function (Callable[[], bool]): Function that returns a boolean indicating state
            timeout (int): Maximum time to wait (in seconds)
            interval (int): Time between checks (in seconds)
            error_msg (str): Message to log if timeout is exceeded

        Returns:
            bool: True if state was reached, False if timeout occurred

        """
        start_time = datetime.now()
        while True:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            if elapsed_time + interval > timeout:
                self.logger.error(error_msg)
                return False
            if check_function():
                return True
            time.sleep(interval)

    def clean_up(self) -> None:
        """Clean up Galaxy resources based on configuration.

        Cleans up histories and workflows according to the 'clean_history' config setting:
        - 'always': Always clean up regardless of job status
        - 'onsuccess': Clean up only if no errors occurred
        - 'never': Never clean up
        """
        clean_his = self.config.get("clean_history", "onsuccess")
        if clean_his not in ["never", "always", "onsuccess"]:
            clean_his = "onsuccess"
        bool_logic = (clean_his == "always") or (
            clean_his == "onsuccess" and not self.err_tracker
        )
        if bool_logic:
            self.purge_histories()
        self.purge_workflow()
        self.logger.info("Clean-up terminated")

    def _add_tag(self, job_id: str, msg_list: list = None) -> None:
        """Add tags to all outputs of a job.

        Args:
            job_id (str): ID of the job to tag
            msg_list (str, optional): Additional tag to add. Defaults to None.

        """
        job_outputs = self.gi.jobs.get_outputs(job_id)
        p_endpoint = self.p_endpoint
        log = False
        if p_endpoint == "None":
            p_endpoint = "Default"
        tag_list = [p_endpoint]
        if msg_list and len(msg_list) > 0:
            tag_list.append(msg_list)
            for output in job_outputs:
                set_id = output["dataset"]["id"]
                self.history_client.update_dataset(
                    history_id=self.history["id"], dataset_id=set_id, tags=tag_list
                )
                log = True
        elif job_id not in self.tagged_jobs[p_endpoint]:
            self.tagged_jobs[p_endpoint].append(job_id)
            for output in job_outputs:
                set_id = output["dataset"]["id"]
                self.history_client.update_dataset(
                    history_id=self.history["id"], dataset_id=set_id, tags=tag_list
                )
                log = True
        if log:
            self.logger.info(f"Added tags: {tag_list} to job {job_id} outputs.")

    def _delete_job_out(self, job_id: str) -> None:
        """Delete all output datasets from a successful job.

        Args:
            job_id (str): ID of the job whose outputs should be deleted

        """
        if not self.gi.jobs.cancel_job(job_id):
            job_outputs = self.gi.jobs.get_outputs(job_id)
            for output in job_outputs:
                set_id = output["dataset"]["id"]
                self.history_client.update_dataset(
                    history_id=self.history["id"], dataset_id=set_id, deleted=True
                )
                self.history_client.delete_dataset(
                    history_id=self.history["id"], dataset_id=set_id, purge=True
                )
                self.logger.info(f"Purging dataset: {set_id}")


class WFPathError(Exception):
    """Exception raised for errors in workflow path configuration.

    Attributes:
        message (str): Explanation of the error

    """

    def __init__(self, message: str) -> None:
        """Initialize WFPathError with an error message.

        Args:
            message (str): Explanation of the error

        """
        self.message = message
        super().__init__(self.message)


class WFInvocation(Exception):
    """Exception raised for errors during workflow invocations.

    Attributes:
        message (str): Explanation of the error

    """

    def __init__(self, message: str) -> None:
        """Initialize WFInvocation with an error message.

        Args:
            message (str): Explanation of the error

        """
        self.message = message
        super().__init__(self.message)
