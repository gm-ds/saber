import time
from src.logger import CustomLogger
import json
from datetime import datetime
from bioblend.galaxy import datasets
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.histories import HistoryClient


class GalaxyTest():
    def __init__(self, url: str, key: str, config: dict = None, class_logger = None):
        #Initialize GalaxyInstance
        self.logger = class_logger if not isinstance(class_logger, CustomLogger) else  CustomLogger()
        self.gi = GalaxyInstance(url, key)
        self.logger.update_log_context()
        self.logger.info("useGalaxy connection initialized")

       # Default configuration
        default_config = {
            "sleep_time": 5,
            "maxwait": 12000,
            "interval": 5,
            "timeout": 12000
        }
        # Merge user-defined config with defaults
        self.config = {**default_config, **(config or {})}


    # Upload necessary data
    def upload_and_build_data(self, history_id: str, workflow_id: str, 
                              inputs_data: dict = None, maxwait: int = None, 
                              interval: int = None, local: bool = None) -> dict:
        if inputs_data is None: 
            inputs_data = self.config['data_inputs']

        if interval is None:
            interval = self.config.get('interval', 5)

        if maxwait is None:
            maxwait = self.config.get('maxwait', 12000)

        if local is None:
            local = self.config.get('local_upload', True)  

        if local: self.switch_pulsar(self.config['default_compute_id'], self.config['name'])
        inputs_dict = inputs_data
        data = dict()
        self.logger.info(f"Uploading and building Datasets")
        for file_name, file_options in inputs_dict.items():
            file_url = file_options['url']
            file_type = file_options['file_type']
            upload = self.gi.tools.put_url(file_url, history_id=history_id, file_name=file_name, file_type=file_type)
            upload_id = upload['outputs'][0]['id']
            wf_input = self.gi.workflows.get_workflow_inputs(workflow_id, label=file_name)[0]
            data[wf_input] = {'id':upload_id, 'src':'hda'}

        # Wait for dataset
        self.logger.info("Waiting for datasets...")
        self._wait_for_dataset(history_id, maxwait, interval)

        return data

    # Manually wait for the dataset
    # for improved logging with custom format
    def _wait_for_dataset(self, history_id: str, maxtime: int = None, interval: int = 5) -> bool:
        if maxtime is None:
            maxtime = self.config.get('maxwait', 12000)
        dataset_client =  datasets.DatasetClient(self.gi)
        all_datasets = dataset_client.get_datasets(history_id=history_id)
        
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
                    
 



    def create_history(self, history_name: str = None, clean_histories=False) -> str:
        if history_name is None:
            history_name = self.config.get('history_name', "Pulsar Endpoints Test")

        # Delete all histories to ensure there's enough free space
        if clean_histories:
            history_client = self.gi.histories.HistoryClient(self.gi)
            for history in history_client.get_histories():
                history_client.delete_history(history['id'], purge=True)

        new_hist = self.gi.histories.create_history(name=history_name)
        self.logger.info(f'Creating History, ID: {new_hist["id"]}')

        return new_hist['id']



    # Clean and Purge Histories from bioblend_test
    def purge_histories(self) -> None:
        history_client = HistoryClient(self.gi)
        for history in history_client.get_histories():
            history_client.delete_history(history['id'], purge=True)
            self.logger.info(f'Purging History, ID: {history["id"]}',)
        


    # Upload Workflow if old one is no more and get workflow id
    def upload_workflow(self, wf_path: str = None ) -> str:
        if wf_path is None:
            wf_path = self.config['ga_path']
    
        wf = self.gi.workflows.import_workflow_from_local_path(wf_path)
        self.logger.info(f'Uploading Workflow, local path: {wf_path}')
        return wf['id']



    # Delete Workflows 
    def purge_workflow(self, workflow_id: str ) -> None:
        self.gi.workflows.delete_workflow(workflow_id)
        self.logger.info(f'Purging Workflow, ID: {workflow_id}')



    # It returns a dict with the status
    def _monitor_job_status(self, invocation_id: str, 
                        timeout: int = None, sleep_time: int = None) -> dict:
        if sleep_time is None:
            sleep_time = self.config.get('sleep_time', 5)

        if timeout is None:
            timeout = self.config.get('timeout', 12000)

        def job_completed():
            # Get job status
            jobs = self.gi.jobs.get_jobs(invocation_id=invocation_id)
            if not jobs:
                return False
                
            current_job = jobs[0]
            job_state = current_job['state']
            job_exit_code = current_job.get('exit_code')
            self.logger.info(f'    {job_state}')

            if job_state == "error":
                self.logger.info(f'The job encountered an error.')
                return True
                
            # Continue monitoring
            if job_state == "ok" and job_exit_code is not None:
                return True
            return False
        
        success = self._wait_for_state(job_completed, timeout, sleep_time, f"Timeout {timeout}s expired.")

        if not success:
            return None

        return self.gi.jobs.get_jobs(invocation_id=invocation_id)[0]


    def _handle_job_completion(self, job: dict) -> int:
        # Cancel job if it's still running
        if job and job['state'] in ['new', 'queued', 'running']:
            self.logger.info('Canceling test job, timeout.')
            self.gi.jobs.cancel_job(job['id'])
            return 1
            
        # Handle completion
        if job and job['exit_code'] == 0:
            self.logger.info('Test job succeeded')
            self.gi.jobs.cancel_job(job['id'])
            return 0
            
        # Handle failure
        job_exit_code = job['exit_code'] if job and job['exit_code'] is not None else 'None'
        self.logger.info(f'Test job failed (exit_code: {job_exit_code})')
        self.gi.jobs.cancel_job(job['id'])
        return 1



    def execute_and_monitor_workflow(self, workflow_id: str, 
                                workflow_input: dict, ID_history: str, timeout: int = None,) -> int:

        if timeout is None:
            timeout = self.config.get('timeout', 12000)        
        # Workflow invocation
        invocation = self.gi.workflows.invoke_workflow(
            workflow_id,
            inputs=workflow_input,
            history_id= ID_history,
            history_name= "Compute testing"

        )
        self.logger.info( f'Invocation id: {invocation["id"]}')
        
        # Monitor the job using the previous function!
        self.logger.info('Waiting until test job finishes. Current state:')
        final_job_status = self._monitor_job_status(
             invocation['id'], timeout
        )
        
        # Handle timeout case
        if final_job_status is None:
            return 1
            
        # Handle job completion
        return self._handle_job_completion(final_job_status)



    # Pretty sure this is need some fixing
    def switch_pulsar(self, p_endpoint: str, name: str = None ) -> None:
        if name is None:
            name = self.config['name']
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
            self.logger.info(f"Testing pulsar endpoint {p_endpoint} "
                        f"from {name} instance")

    def _wait_for_state(self, check_function, timeout: int, interval: int, error_msg: str):
        start_time = datetime.now()
        while True:
            elapsed_time = (datetime.now() - start_time).total_seconds()
            if elapsed_time + interval > timeout:
                self.logger.error(error_msg)
                return False
            if check_function():
                return True
            time.sleep(interval)