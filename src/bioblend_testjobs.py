#!/usr/bin/env python3


import time
import json
from pathlib import Path
from src.globals import API_EXIT, PATH_EXIT, TOOL_NAME
from datetime import datetime, timedelta
from src.logger import CustomLogger
from bioblend.galaxy import datasets
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.histories import HistoryClient


class GalaxyTest():
    '''
    Creates a GalaxyInstance using bioblend, and logs operations with a custom logger.
    Both API and mail/password are supported.

    Set some defaults if not present in the dict passed for initialization.

    :type url: str
    :param url: API key of a usegalaxy instance, has precedence over mail and password
    :type email: str 
    :param email: Optional, to be used along the password of the account
    :type gpassword: str 
    :param gpassword: Optional, to be used along the email of the account
    :type config: dict
    :param config: Dictionary conataining everything needed for the test jobs excluding the workflow
    :type class_logger: Any
    :param class_logger: Logger instace used by the class.

    '''
    def __init__(self, url: str, key: str, email: str = None, gpassword: str = None, 
                 config: dict = None, class_logger = None):
        #Initialize GalaxyInstance
        self.logger = class_logger if isinstance(class_logger, CustomLogger) else  CustomLogger(TOOL_NAME)
        self.gi = GalaxyInstance(url, email, gpassword) if ((email is not None) and (gpassword is not None)) else GalaxyInstance(url, key)
        self.logger.update_log_context()
        self.logger.info("useGalaxy connection initialized")

       # Default configuration
        default_config = {
            "sleep_time": 5,
            "maxwait": 12000,
            "interval": 5,
            "timeout": 12000,
            "history_name": "Pulsar Endpoints Test"
        }
        # Merge user-defined config with defaults
        self.config = {**default_config, **(config or {})}
        self.history_client = HistoryClient(self.gi)
        self.history = None
        self.wf = None



    def test_job_set_up(self, inputs_data: dict = None, maxwait: int = None, 
                              interval: int = None, local: bool = None) -> dict:
        '''
        Sets up new histories and upload workflows.

        :type inputs_data: dict
        :param inputs_data: Dictionary with the inputs for the workflow

        :type maxwait: int
        :param maxwait: Maximum wait, in seconds, during upload of the datasets. Defaults to 12000

        :type interval: int
        :param interval: Interval between status checks, defaults to 5s.

        :type local: bool
        :param local:   Deafults to True. When False it will not change the User
                        Preferences, possibly trying to upload the datasets through a Pulsar Endpoint.
    
        '''
        inputs_data = self.config['data_inputs'] if inputs_data is None else inputs_data
        interval = self.config['interval'] if interval is None else interval
        maxwait = self.config['maxwait'] if maxwait is None else maxwait
        local = self.config.get('local_upload', True) if local is None else local

        if local: self.switch_pulsar(self.config['default_compute_id'], self.config['name'])
        self._create_history()
        self._upload_workflow()
        inputs_dict = inputs_data
        data = dict()
        self.logger.info(f"Uploading and building Datasets")
        for file_name, file_options in inputs_dict.items():
            file_url = file_options['url']
            file_type = file_options['file_type']
            upload = self.gi.tools.put_url(file_url, history_id=self.history['id'], file_name=file_name, file_type=file_type)
            upload_id = upload['outputs'][0]['id']
            wf_input = self.gi.workflows.get_workflow_inputs(self.wf['id'], label=file_name)[0]
            data[wf_input] = {'id':upload_id, 'src':'hda'}

        # Wait for dataset
        self.logger.info("Waiting for datasets...")
        self._wait_for_dataset(maxwait, interval)

        return data



    def _wait_for_dataset(self, maxtime: int = None, interval: int = 5) -> bool:
        '''
        Wait for dataset upload.
        '''
        maxtime = self.config['maxwait'] if maxtime is None else maxtime
        dataset_client =  datasets.DatasetClient(self.gi)
        all_datasets = dataset_client.get_datasets(history_id=self.history['id'])
        
        def check_dataset_ready():
            for dataset in all_datasets:
                dataset_id = dataset['id']

                dataset_info = dataset_client.show_dataset(dataset_id)
                state = dataset_info['state']
                
                if state in {"ok", "empty", "error", "discarded", "failed_metadata"}:
                    if state != "ok":
                        self.logger.warning(f"Dataset {dataset_id} is in terminal state {state}")
                        self.logger.error(f"Upload of Dataset {dataset_id} failed")
                        return True
                    if state in {"ok", "empty"}:
                        continue
                self.logger.info(f"Dataset {dataset_id} is in non-terminal state {state}")

                return False
            return True
        return self._wait_for_state(check_dataset_ready, maxtime, interval, "Upload time exceeded")
                    
 



    def _create_history(self, history_name: str = None) -> None:
        '''
        Create a new History, while deleting permanently older histories (>1 week) to ensure enough space.

        :type history_name: str
        :param history_name: Optional, defaults to "Pulsar Endpoints Test"
        '''
        if history_name is None:
            history_name = self.config.get('history_name', "Pulsar Endpoints Test")

        # Delete older histories to ensure there's enough free space
        self.purge_histories(False)

        self.history = self.history_client.create_history(name=history_name)
        self.logger.info(f'Creating History, ID: {self.history["id"]}')




    def purge_histories(self, purge_new: bool = True, purge_old: bool = True) -> None:
        '''
        Purge histories with the same names used during the tests or older than 1 week.

        :type purge_new: bool
        :param purge_new: Defaults True - purges all the histories with the name used in the tests

        :type purge_old: bool
        :param purge_old: Defaults True - purges ALL histories older than one week.
        '''
        if self.history is not None:
            for history in self.history_client.get_histories():
                if history['name'] == self.config.get('history_name') and purge_new:
                    self.history_client.delete_history(history['id'], purge=True)
                    self.logger.info(f'Purging History, ID: {history["id"]}, Name: {history["name"]}')
                if (datetime.today() - datetime.strptime(history['update_time'],
                                                        "%Y-%m-%dT%H:%M:%S.%f")) > timedelta(weeks=1) and purge_old: 
                    self.history_client.delete_history(history['id'], purge=True)
                    self.logger.info(f'Purging History, ID: {history["id"]}, Name: {history["name"]}')



    # Rename History to keep it if an error occurs
    def _update_history_name(self, msg: str = 'ERROR') -> None:
        '''
        Changes the name of a history. Used when a job fails or timeouts.

        :type msg: str, optional
        :param msg: Small message that is added to the history name to provide some information. Defaults to ERROR
        '''
        message = f"{msg}-{self.config.get('history_name')}"
        self.history_client.update_history(self.history['id'], name=message)
        self.logger.info(f"History name updated to: {message}")
            
        

    def _upload_workflow(self, wf_path: str = None) -> None:
        '''
        Upload Workflow file to usegalaxy.

        :type wf_path: str
        :param wf_path: Path to the workflow file from config.
        '''
        wf_path = self.config.get('ga_path', None) if wf_path is None else wf_path
        if wf_path is None:
            self.logger.error("No workflow path provided in config or arguments.")
            raise SystemExit(PATH_EXIT)

        wf_path = Path(wf_path).expanduser()

        if not wf_path.is_absolute():
            config_path = self.config.get('config_path', None)
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
            self.wf = self.gi.workflows.import_workflow_from_local_path(str(wf_path))
            self.logger.info(f'Uploading Workflow, local path: {wf_path}')
        else:
            self.logger.error(f"Workflow path does not exist: {wf_path}")
            raise SystemExit(PATH_EXIT)




    def purge_workflow(self) -> None:
        '''
        Delete permanently the workflow uploaded for the test
        '''
        if self.wf is not None:
            self.gi.workflows.delete_workflow(self.wf['id'])
            self.logger.info(f'Purging Workflow, ID: {self.wf["id"]}')



    def _tool_id_split(self, tool_id: str) -> str:
        '''
        Remove all characters before "/devteam" inclusively, to avoid clutter in the log.
        If the string is not present it leaves the input untouched
        '''
        if "/devteam/" in tool_id:
            return tool_id.split("/devteam/")[1]
        else:
            return tool_id


    def _monitor_job_status(self, invocation_id: str, 
                        timeout: int = None, sleep_time: int = None) -> dict:
        '''
        Monitor the status of a job invocation.

        :param invocation_id: The ID of the workflow invocation to monitor.
        :type invocation_id: str
        :param timeout: Maximum time (in seconds) to wait for job completion. Defaults to 12000s.
        :type timeout: int, optional
        :param sleep_time: Time (in seconds) to wait between status checks. Defaults to 5s.
        :type sleep_time: int, optional
        :return: A dictionary containing the final job status.
        :rtype: dict
        '''
        sleep_time = self.config["sleep_time"] if sleep_time is None else sleep_time
        timeout = self.config["timeout"] if timeout is None else timeout

        def job_completed():
            # Get job status
            jobs = self.gi.jobs.get_jobs(invocation_id=invocation_id)
            if not jobs:
                return False
            
            for i in range(len(jobs)):
                current_job = jobs[i]
                job_state = current_job['state']
                job_exit_code = current_job.get('exit_code')
                tool_id = self._tool_id_split(current_job.get("tool_id"))
                self.logger.info(f'    {job_state}    Tool ID: {tool_id}')

                if job_state == "error":
                    self.logger.info(f'The job encountered an error.')
                    if i == len(jobs)-1:
                        return True
                    
                # Continue monitoring
                if job_state == "ok" and job_exit_code is not None:
                    if i == len(jobs)-1:
                        return True        
            return False
        
        self._wait_for_state(job_completed, timeout, sleep_time, f"Timeout {timeout}s expired.")

        return self.gi.jobs.get_jobs(invocation_id=invocation_id)



    def _handle_job_completion(self, jobs: list[dict[str, any]]) -> dict[dict[dict[list[dict[str, any]]]]]:
        '''
        Job completion handler. Changes History name in case of failures.

        :type job: dict
        :param job: Dict containing the job informations
        :return: Integer to indicate failure or success
        :rtype: int
        '''
        timeout_jobs = {}
        successful_jobs = {}
        failed_jobs = {}
        for job in jobs:

            # Cancel job if it's still running
            if job and job['state'] in ['new', 'queued', 'running']:
                #self.logger.info('Canceling test job, timeout.')
                self.logger.info(f'Job {job["id"]} failed due to timeout:')
                self.logger.info(f'         Tool: {self._tool_id_split(job["tool_id"])}')
                timeout_jobs[job['id']] = {"INFO":self.gi.jobs.show_job(job['id']),
                                              "PROBLEMS": self.gi.jobs.get_common_problems(job['id']),
                                              "METRICS": self.gi.jobs.get_metrics(job['id'])
                                              }
                self._update_history_name('TIMEOUT')
                
            # Handle completion
            elif job and job['exit_code'] == 0:
                self.logger.info(f'Job {job["id"]} succeeded:')
                self.logger.info(f'         Tool: {self._tool_id_split(job["tool_id"])}')
                successful_jobs[job['id']] = {"INFO": self.gi.jobs.show_job(job['id']),
                                              "METRICS": self.gi.jobs.get_metrics(job['id'])
                                              }
                self.gi.jobs.cancel_job(job['id'])

            else:
                
                # Handle failure
                job_exit_code = job['exit_code'] if job and job['exit_code'] is not None else 'None'
                self.logger.info(f'Job {job["id"]} failed (exit_code: {job_exit_code}):')
                self.logger.info(f'         Tool: {self._tool_id_split(job["tool_id"])}')
                failed_jobs[job['id']] = {"INFO":self.gi.jobs.show_job(job['id']),
                                  "PROBLEMS": self.gi.jobs.get_common_problems(job['id']),
                                  "METRICS": self.gi.jobs.get_metrics(job['id'])}
                self._update_history_name()
                #self.gi.jobs.cancel_job(job['id'])
        return_values = {"SUCCESSFUL_JOBS": successful_jobs, 
                                     "TIMEOUT_JOBS": timeout_jobs, 
                                     "FAILED_JOBS": failed_jobs}
        return return_values



    def execute_and_monitor_workflow(self, workflow_input: dict, timeout: int = None) -> dict[list[dict[str, any]]]:
        '''
        Executes a workflow and monitors its status until completion or timeout.

        :param workflow_input: A dictionary containing the input parameters for the workflow.
        :type workflow_input: dict
        :param timeout: Maximum time (in seconds) to wait for the workflow to complete. Defaults to 12000s.
        :type timeout: int, optional
        :return: The exit code or status of the executed workflow.
        :rtype: int
        '''
        timeout = self.config["timeout"] if timeout is None else timeout       
        # Workflow invocation
        invocation = self.gi.workflows.invoke_workflow(
            self.wf['id'],
            inputs=workflow_input,
            history_id= self.history['id']
        )
        self.logger.info( f'Invocation id: {invocation["id"]}')
        
        # Monitor the job using the previous function!
        self.logger.info('Waiting until test job finishes. Current state:')
        final_job_status = self._monitor_job_status(
             invocation['id'], timeout
        )
        
        # Handle job completion
        return self._handle_job_completion(final_job_status)



    def switch_pulsar(self, p_endpoint: str, name: str = None ) -> None:
        '''
        Switches to a different Pulsar endpoint for processing.

        :param p_endpoint: The Pulsar endpoint to switch to.
        :type p_endpoint: str
        :param name: An optional name for the Pulsar instance. If not provided, the config value will be used.
        :type name: str, optional
        '''
        name = self.config['name'] if name is None else name
        user_id = self.gi.users.get_current_user()['id']
        prefs = self.gi.users.get_current_user().get('preferences', {}).get('extra_user_preferences', {})
        new_prefs = json.loads(prefs).copy() # TODO: find a workaround to not use the json library only for this bit
        new_prefs.update({'distributed_compute|remote_resources' : p_endpoint})

        if prefs != new_prefs:
            self.logger.info('Updating pulsar endpoint in user preferences')
            self.gi.users.update_user(user_id=user_id, user_data = new_prefs)
            if p_endpoint == "None":
                p_endpoint = "Default"
            self.logger.update_log_context( name, p_endpoint)
            self.logger.info(f"Switching to pulsar endpoint {p_endpoint} "
                        f"from {name} instance")



    def _wait_for_state(self, check_function, timeout: int, interval: int, error_msg: str):
        '''
        Waits for a specific state to be reached by periodically checking the provided function.

        :param check_function: A function that returns a boolean to indicate its state.
        :type check_function: callable
        :param timeout: The maximum time to wait for the state to be reached.
        :type timeout: int
        :param interval: The time to wait between state checks.
        :type interval: int
        :param error_msg: The message to log if the timeout is exceeded.
        :type error_msg: str
        :return: True if the desired state was reached, otherwise False.
        :rtype: bool
        '''
        start_time = datetime.now()
        while True:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            if elapsed_time + interval > timeout:
                self.logger.error(error_msg)
                return False
            if check_function():
                return True
            time.sleep(interval)
