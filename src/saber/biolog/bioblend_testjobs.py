#!/usr/bin/env python3

import re
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from bioblend import ConnectionError
from bioblend.galaxy import GalaxyInstance, datasets
from bioblend.galaxy.histories import HistoryClient

from saber.biolog.loglike import LoggerLike
from saber.biolog.logger import CustomLogger


class JobState(Enum):
    """Enumeration of Galaxy job states."""

    OK = "ok"
    ERROR = "error"
    RUNNING = "running"
    QUEUED = "queued"
    WAITING = "waiting"
    NEW = "new"
    EMPTY = ""
    DISCARDED = "discarded"
    FAILED_METADATA = "failed_metadata"


class CleanupPolicy(Enum):
    """History cleanup policies."""

    ON_SUCCESS = "onsuccess"
    SUCCESSFUL_ONLY = "successful_only"
    NEVER = "never"
    ALWAYS = "always"


@dataclass
class GalaxyTesterConfig:
    """Configuration class for Galaxy testing with validation."""

    # Required fields
    url: str
    name: str
    ga_path: str
    endpoints: List[str]
    data_inputs: Dict[str, Dict[str, str]]
    default_compute_id: str

    # Optional fields with defaults
    api: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    clean_history: str = "onsuccess"
    config_path: Optional[str] = None
    delete_after: float = 5.0
    history_name: str = "SABER"
    local_upload: bool = True
    interval: int = 5
    maxwait: int = 12000
    sleep_time: int = 5
    timeout: int = 12000
    date_string: str = ""
    date: any = None

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate_required_fields()
        self._validate_clean_history()
        self._validate_auth_fields()
        self._validate_numeric_fields()
        self._validate_paths()

    def _validate_required_fields(self) -> None:
        """Validate that all required fields are provided."""
        required_fields = [
            "url",
            "name",
            "ga_path",
            "endpoints",
            "data_inputs",
            "default_compute_id",
        ]
        for field_name in required_fields:
            value = getattr(self, field_name)
            if value is None or (isinstance(value, (list, dict)) and not value):
                raise ValueError(f"Required field '{field_name}' is missing or empty")

    def _validate_auth_fields(self) -> None:
        """Validate authentication configuration."""
        has_api = self.api is not None
        has_email_pass = self.email is not None and self.password is not None

        if not has_api and not has_email_pass:
            raise ValueError(
                "Either 'api' key or both 'email' and 'password' must be provided"
            )

        if has_api and has_email_pass:
            raise ValueError("Provide either 'api' key OR email/password, not both")

    def _validate_numeric_fields(self) -> None:
        """Validate numeric field ranges."""
        if self.delete_after < 0:
            raise ValueError("delete_after must be non-negative")
        if self.interval <= 0:
            raise ValueError("interval must be positive")
        if self.maxwait <= 0:
            raise ValueError("maxwait must be positive")
        if self.sleep_time <= 0:
            raise ValueError("sleep_time must be positive")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")

    def _validate_paths(self) -> None:
        """Validate path fields."""
        if self.ga_path and not isinstance(self.ga_path, (str, Path)):
            raise ValueError("ga_path must be a string or Path object")

    def _validate_clean_history(self) -> None:
        """Validate the clean_history policy."""
        valid_policies = [policy.value for policy in CleanupPolicy]
        if self.clean_history not in valid_policies:
            self.clean_history = CleanupPolicy.ON_SUCCESS.value


class GalaxyTest:
    """Creates a GalaxyInstance using BioBlend, and logs operations with a custom logger.

    Both API and mail/password are supported. Sets some defaults if not present in the dict passed
    for initialization.

    Args:
        config (dict, optional): User-defined configuration options to override defaults.
        Logger (LoggerLike, optional): Logger instance for logging messages. Defaults to None.
        **kwargs (dict): Key-value pairs to be passed instead of config.

    """

    def __init__(
        self,
        config: Optional[dict[str, Any]] = None,
        Logger: Optional[LoggerLike] = None,
        **kwargs: Optional[dict[str, Any]],
    ) -> None:
        """Initializes a bioblend Galaxy instance and sets up configuration for job management.

        Args:
            config (dict, optional): User-defined configuration options to override defaults.
            Logger (LoggerLike, optional): Logger instance for logging messages. Defaults to None.
            **kwargs (dict): Key-value pairs to be passed instead of config.

        Attributes:
            config.api (str): API key for Galaxy instance
            config.clean_history (str): History cleanup policy, defaults to "onsuccess"
            config.config_path (str): Path to the configuration file
            config.data_inputs (dict | object): Input data for the workflow, must be provided
            config.default_compute_id (str | object): Default compute endpoint ID, must be provided
            config.delete_after (float): Time in days to keep histories before deletion, defaults to 5
            config.email (str): Email for Galaxy user, defaults to None
            config.endpoints (list | object): List of compute endpoints to test, must be provided
            config.ga_path (str | object): Path to the workflow file, must be provided
            config.history_name (str): Name for the Galaxy history, defaults to "SABER"
            config.local_upload (bool): Whether to use local upload, defaults to True
            config.interval (int): Interval between status checks, defaults to 5 seconds
            config.maxwait (int): Maximum wait time for uploads, defaults to 12000 seconds
            config.name (str | object): Name of the Galaxy instance, must be provided
            config.password (str): Password for Galaxy user, defaults to None
            config.sleep_time (int): Sleep time between checks, defaults to 5 seconds
            config.timeout (int): Maximum time to wait for job completion, defaults to 12000 seconds
            config.url (str | object): URL of the Galaxy instance, must be provided
            logger: Logger instance for logging.
            gi: GalaxyInstance object for interacting with the Galaxy server.
            p_endpoint (str): Placeholder for endpoint information.
            err_tracker (bool): Error tracking flag.
            current_date (str): Current date and time string for history naming.
            history_client (HistoryClient): Client for managing Galaxy histories.
            history: Placeholder for the current Galaxy history.
            wf: Placeholder for the current workflow.
            invocation_ids (dict): Dictionary to store invocation IDs for each endpoint.
            tagged_jobs (dict): Dictionary to store tagged jobs for each endpoint.

        Returns:
            None

        Raises:
            None
        """
        # Setup instance attributes
        self.gi: GalaxyInstance = None
        self.user: dict = None
        self.history = None
        self.wf = None
        self.p_endpoint = ""
        self.err_tracker = False
        self.tagged_jobs = {}
        self.invocation_ids = {}
        self.current_date = datetime.now().strftime("%-d/%-m/%y %H:%M")

        # Validate configuration input
        if config and kwargs:
            raise ValueError("Pass either 'config' or keyword arguments, not both.")
        config = config or kwargs
        self.config = GalaxyTesterConfig(**config)

        # Tagged Jobs dictionary initialization
        for pe in self.config.endpoints:
            if pe == "None":
                pe = "Default"
            self.tagged_jobs[pe] = []

        # Initialize GalaxyInstanceLogger
        self.logger = Logger

        # Set history name with current date
        self.history_name = f"{self.config.history_name} {self.current_date}"

        # Initialize Galaxy instance
        self._initialize_galaxy_connection()

        # Update logging context
        self._update_log_context()
        self.logger.info("useGalaxy connection initialized")

        # Initialize history client
        self.history_client = HistoryClient(self.gi)

        # Delete older histories
        self.purge_histories()

    def _initialize_galaxy_connection(self) -> None:
        """Initialize the Galaxy connection based on authentication method."""
        if self.config.email and self.config.password:
            self.gi = GalaxyInstance(
                self.config.url, self.config.email, self.config.password
            )
        else:
            self.gi = GalaxyInstance(self.config.url, self.config.api)

        self.user = self.gi.users.get_current_user()

    def _update_log_context(
        self, endpoint: Optional[str] = None, name: Optional[str] = None
    ) -> None:
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
        name = name or self.config.name
        endpoint = endpoint or "Default"
        if endpoint == "None":
            endpoint = "Default"
        self.p_endpoint = endpoint
        if isinstance(self.logger, CustomLogger):
            self.logger.update_log_context(instance_name=name, endpoint=endpoint)

    def test_job_set_up(
        self,
        inputs_data: Optional[dict] = None,
        maxwait: Optional[int] = None,
        interval: Optional[int] = None,
        local: Optional[bool] = True,
    ) -> Dict[str, Dict[str, str]]:
        """Sets up new histories and upload workflows.

        This method prepares the Galaxy instance for testing, first checking whether to upload
        datasets locally or through a Pulsar endpoint. It creates an empty history, and uploads
        the workflow file specified in the configuration.
        After the workflow is uploaded, it creates the workflow inputs ands uploads the datasets.
        The datasets statuses are monitored during upload.

        Args:
            inputs_data (dict, optional): Dictionary with the inputs for the workflow
            maxwait (int, optional): Maximum wait, in seconds, during upload of the datasets. Defaults to 12000
            interval (int, optional): Interval between status checks, defaults to 5s.
            local (bool, optional): Defaults to True. When False it will not change the User
                Preferences, possibly trying to upload the datasets through a Pulsar Endpoint.

        Returns:
            dict: Dictionary containing the workflow inputs

        """
        inputs_data = inputs_data or self.config.data_inputs
        interval = interval or self.config.interval
        maxwait = maxwait or self.config.maxwait
        local = local or self.config.local_upload

        if local:
            self.switch_pulsar(self.config.default_compute_id, name=self.config.name)
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

    def _wait_for_dataset(
        self, maxtime: Optional[int] = None, interval: Optional[int] = 5
    ) -> bool:
        """Wait for dataset upload.

        This method iterates a helper function to check if all datasets are in a terminal state.

        Args:
            maxtime (int, optional): Maximum time to wait. Defaults to config value.
            interval (int, optional): Interval between checks. Defaults to 5.

        Returns:
            bool: True if datasets are ready, False if timeout occurred

        """
        maxtime = maxtime or self.config.maxwait
        dataset_client = datasets.DatasetClient(self.gi)
        all_datasets = dataset_client.get_datasets(history_id=self.history["id"])

        def check_dataset_ready() -> bool:
            """Check if datasets are in terminal state.

            Returns:
                bool: True if all datasets are in terminal state, False otherwise.
            """
            for dataset in all_datasets:
                dataset_id = dataset["id"]

                dataset_info = dataset_client.show_dataset(dataset_id)
                state = dataset_info["state"]

                if state in [
                    JobState.OK.value,
                    JobState.EMPTY.value,
                    JobState.ERROR.value,
                    JobState.DISCARDED.value,
                    JobState.FAILED_METADATA.value,
                ]:
                    if state != JobState.OK.value:
                        self.logger.warning(
                            f"Dataset {dataset_id} is in terminal state {state}"
                        )
                        self.logger.error(f"Upload of Dataset {dataset_id} failed")
                        return True
                    if state in [JobState.OK.value, JobState.EMPTY.value]:
                        continue
                self.logger.info(
                    f"Dataset {dataset_id} is in non-terminal state {state}"
                )

                return False
            return True

        return self._wait_for_state(
            check_dataset_ready, maxtime, interval, "Upload time exceeded"
        )

    def _create_history(self, history_name: Optional[str] = None) -> None:
        """Create a new History.

        Deletes permanently older histories to ensure enough space.

        Args:
            history_name (str, optional): Defaults to "Pulsar Endpoints Test"

        """
        history_name = history_name or self.history_name

        self.logger.info("Creating History...")
        self.history = self.history_client.create_history(name=history_name)
        self.logger.info(f"         History ID: {self.history['id']}")

    def _safe_delete_history(self, id: str, purge: bool) -> None:
        """Safely delete a history, handling immutable histories.

        Args:
            id (str): History ID to delete
            purge (bool): Whether to purge the history

        """
        try:
            self.history_client.delete_history(history_id=id, purge=purge)
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
        """Purge histories with the same names used during tests or older.

        Histories deletion times can be configured (in days) throgh config, under the key `delete_after`

        Args:
            purge_new (bool, optional): Defaults True - purges all histories with test name
            purge_old (bool, optional): Defaults True - purges ALL histories older than specified days in the configuration file.

        """
        if not self.history_client:
            return

        histories = self.history_client.get_histories()
        cutoff_date = datetime.today() - timedelta(days=self.config.delete_after)
        config_clean = self._clean_string(self.history_name)

        for history in histories:
            history_name = history.get("name", "")
            if purge_new and self.history_name == history_name:
                self.logger.info(
                    f"Purging History, ID: {history['id']}, Name: {history['name']}"
                )
                self._safe_delete_history(history["id"], purge=True)
                continue

            if purge_old:
                history_details = self.history_client.show_history(
                    history_id=history["id"], keys=["create_time"]
                )
                create_time = datetime.strptime(
                    history_details["create_time"], "%Y-%m-%dT%H:%M:%S.%f"
                )

                if create_time < cutoff_date:
                    history_clean = self._clean_string(history_name)

                    if config_clean in history_clean or any(
                        config_clean == word for word in history_clean.split()
                    ):
                        self.logger.info(
                            f"Purging old history, ID: {history['id']}, Name: {history['name']}"
                        )
                        self._safe_delete_history(history["id"], purge=True)
                        return

    def _upload_workflow(self, wf_path: Optional[Union[str, Path]] = None) -> None:
        """Upload Workflow file to usegalaxy.* instance.

        Args:
            wf_path (str, optional): Path to the workflow file

        Raises:
            WFPathError: If no workflow path is provided or path doesn't exist

        """
        wf_path = Path(wf_path or self.config.ga_path).expanduser()

        if not wf_path.is_absolute():
            wf_path = self._resolve_workflow_path(wf_path)

        if not wf_path.exists():
            raise WFPathError(f"Workflow path does not exist: {wf_path}")

        self.logger.info(f"Uploading Workflow, local path: {wf_path}")
        self.wf = self.gi.workflows.import_workflow_from_local_path(str(wf_path))

    def _resolve_workflow_path(self, wf_path: Path) -> Path:
        """Resolve relative workflow path by checking config directory and CWD.

        Args:
            wf_path: Relative workflow path.

        Returns:
            Resolved absolute path.
        """
        if self.config.config_path:
            config_based_path = (
                Path(self.config.config_path).parent / wf_path
            ).resolve()
            if config_based_path.exists():
                return config_based_path

        cwd_based_path = (Path.cwd() / wf_path).resolve()
        if cwd_based_path.exists():
            return cwd_based_path

        return wf_path.resolve()

    def purge_workflow(self) -> None:
        """Delete permanently the workflow uploaded for the test."""
        if self.wf:
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
        self,
        timeout: Optional[int] = None,
        sleep_time: Optional[int] = None,
        wait_for_inv: Optional[str] = None,
    ) -> None:
        """Monitor the status of a job invocation.

        This method checks the status of jobs in a workflow invocation  with a helper function that stops being iterated when it return true.
        When wait_for_inv is not None, it waits for all jobs of a single invocation to simply start.

        Args:
            timeout (int, optional): Maximum time (in seconds) to wait. Defaults to 12000s. It is halfed for initial job start.
            sleep_time (int, optional): Time between status checks. Defaults to 5s
            wait_for_inv (str, optional): If not None, waits for all jobs to start before checking completion. Defaults to None.

        Returns:
            None

        """
        sleep_time = sleep_time or self.config.sleep_time
        timeout = timeout or self.config.timeout
        pe_list = self.config.endpoints.copy()
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
                if job_state not in [
                    JobState.OK.value,
                    JobState.ERROR.value,
                    JobState.RUNNING.value,
                    JobState.QUEUED.value,
                    JobState.WAITING.value,
                ]:
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
                    if job_state in [JobState.OK.value, JobState.ERROR.value]:
                        terminal_state_job.append(current_job["id"])
                    # Continue monitoring
                    if job_state not in [JobState.OK.value, JobState.ERROR.value]:
                        one_inv_completed = False
                        all_jobs_completed = False

                if one_inv_completed:
                    pe_list.remove(pe)

            return all_jobs_completed

        if wait_for_inv:
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

    def _handle_job_completion(self) -> dict[dict[dict[list[dict[str, any]]]]]:
        """Job completion handler. Add tags describing failures or other states.

        This method iterates through the jobs in the workflow invocations done for each endpoint, organizes and store the queried results in a dictionary.

        Args:
            jobs (list[dict[str, any]]): List of job dictionaries

        Returns:
            dict: Dictionary containing successful, timeout and failed jobs with their details

        """
        return_values = {}
        if self.config.name not in return_values:
            return_values[self.config.name] = {}
        for pe in self.config.endpoints:
            self._update_log_context(endpoint=pe)
            compute_id = pe if pe != "None" else "Default"

            if compute_id not in return_values[self.config.name]:
                return_values[self.config.name][compute_id] = {}
                for key in [
                    "SUCCESSFUL_JOBS",
                    "RUNNING_JOBS",
                    "QUEUED_JOBS",
                    "NEW_JOBS",
                    "WAITING_JOBS",
                    "FAILED_JOBS",
                ]:
                    return_values[self.config.name][compute_id][key] = {}

            if self.invocation_ids.get(pe) in self.invocation_ids.values():
                jobs = self.gi.jobs.get_jobs(invocation_id=self.invocation_ids[pe])

            for job in jobs:
                if job:
                    if job["state"] in [
                        JobState.NEW.value,
                        JobState.QUEUED.value,
                        JobState.RUNNING.value,
                        JobState.WAITING.value,
                    ]:
                        self.logger.info(f"Job {job['id']} reached tool timeout:")
                        self.logger.info(
                            f"         Tool: {self._tool_id_split(job['tool_id'])} Status: {job['state']}"
                        )
                        self._add_tag(job["id"], msg_list=f"saber_{job['state']}")
                        self.err_tracker = True
                        if job["state"] == JobState.RUNNING.value:
                            return_values[self.config.name][compute_id]["RUNNING_JOBS"][
                                job["id"]
                            ] = {
                                "INFO": self.gi.jobs.show_job(job["id"]),
                                "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                                "METRICS": self.gi.jobs.get_metrics(job["id"]),
                            }
                        if job["state"] == JobState.NEW.value:
                            return_values[self.config.name][compute_id]["NEW_JOBS"][
                                job["id"]
                            ] = {
                                "INFO": self.gi.jobs.show_job(job["id"]),
                                "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                                "METRICS": self.gi.jobs.get_metrics(job["id"]),
                            }
                        if job["state"] == JobState.QUEUED.value:
                            return_values[self.config.name][compute_id]["QUEUED_JOBS"][
                                job["id"]
                            ] = {
                                "INFO": self.gi.jobs.show_job(job["id"]),
                                "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                                "METRICS": self.gi.jobs.get_metrics(job["id"]),
                            }
                        if job["state"] == JobState.WAITING.value:
                            return_values[self.config.name][compute_id]["WAITING_JOBS"][
                                job["id"]
                            ] = {
                                "INFO": self.gi.jobs.show_job(job["id"]),
                                "PROBLEMS": self.gi.jobs.get_common_problems(job["id"]),
                                "METRICS": self.gi.jobs.get_metrics(job["id"]),
                            }

                    # Handle completion
                    elif job["exit_code"] == 0 or job["state"] == JobState.OK.value:
                        self.logger.info(f"Job {job['id']} succeeded:")
                        self.logger.info(
                            f"         Tool: {self._tool_id_split(job['tool_id'])}"
                        )
                        return_values[self.config.name][compute_id]["SUCCESSFUL_JOBS"][
                            job["id"]
                        ] = {
                            "INFO": self.gi.jobs.show_job(job["id"]),
                            "METRICS": self.gi.jobs.get_metrics(job["id"]),
                        }
                        if self.config.clean_history == "successful_only":
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
                        return_values[self.config.name][compute_id]["FAILED_JOBS"][
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
        timeout = timeout or self.config.timeout
        for pe in self.config.endpoints:
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
        self,
        p_endpoint: Optional[str] = None,
        name: Optional[str] = None,
        original_prefs: Optional[bool] = False,
    ) -> None:
        """Switches to a different Pulsar endpoint for processing.

        Args:
            p_endpoint (str, Optional): The Pulsar endpoint to switch to, defaults to default_compute_id in config.
            name (str, optional): Name for the Pulsar instance. Defaults to config value
            original_prefs (bool, optional): If True, restores preferences. Defaults to False.

        """
        name = name or self.config.name
        p_endpoint = (
            self.config.default_compute_id if p_endpoint is None else p_endpoint
        )
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
            p_endpoint = (
                new_prefs.get("distributed_compute|remote_resources")
                if original_prefs
                else p_endpoint
            )
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
        # "successful_only" is the default behavior.
        bool_logic = (self.config.clean_history == "always") or (
            self.config.clean_history == "onsuccess" and not self.err_tracker
        )
        if bool_logic:
            self.purge_histories()
        self.purge_workflow()
        self.logger.info("Clean-up terminated")

    def _add_tag(self, job_id: str, msg_list: list = None) -> None:
        """Add tags to all outputs of a job.

        This method adds tags containing the Pulsar endpoint name and a optional message.

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
