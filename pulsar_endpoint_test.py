#!/usr/bin/env python3

import sys
import os
import time
from src.logger import CustomLogger, ContextFilter
import json
import yaml
import bioblend
from datetime import datetime
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.histories import HistoryClient

# Global Variables
SLEEP_TIME = 5
logger = ''


# Loading Config using a YAML file
def load_config(config_path='configs/settings.yaml'):
    try:
        with open(config_path, 'r') as f:
            logger.info(f"Loading Config")
            return yaml.safe_load(f)
        
    except (FileNotFoundError, PermissionError) as e:
        logger.critical(f"Error reading {config_path}: {e}")
        sys.exit(1)

    except yaml.YAMLError as e:
        logger.critical(f"YAML parsing error: {e}")
        sys.exit(1)



# Upload necessary data
def upload_and_build_data(gi, history_id: str, workflow_id: str, inputs_data: dict, maxwait: int = 12000, interval: int = 5) -> dict:
    if not isinstance(maxwait, int):
        maxwait = 12000
    inputs_dict = inputs_data
    data = dict()
    start_time = datetime.now()
    logger.info(f"Uploading and building Datasets")
    for file_name, file_options in inputs_dict.items():
        file_url = file_options['url']
        file_type = file_options['file_type']
        upload = gi.tools.put_url(file_url, history_id=history_id, file_name=file_name, file_type=file_type)
        upload_id = upload['outputs'][0]['id']
        wf_input = gi.workflows.get_workflow_inputs(workflow_id, label=file_name)[0]
        data[wf_input] = {'id':upload_id, 'src':'hda'}

    # Wait for dataset
    logger.info("Waiting for datasets...")
    wait_for_dataset(gi, history_id, start_time, maxwait, interval)

    return data



# Manually wait for the dataset
# for improved logging with custom format
def wait_for_dataset(gi: GalaxyInstance, history_id: str, start_time: datetime, maxtime: int = 12000, interval: int = 5) -> None:
    dataset_client =  bioblend.galaxy.datasets.DatasetClient(gi)
    all_datasets = dataset_client.get_datasets(history_id=history_id)
    
    for dataset in all_datasets:
        dataset_id = dataset['id']
        prev_state = None
        
        while True:

            # Check timeout
            elapsed_time = (datetime.now() - start_time).total_seconds()
            if elapsed_time + interval > maxtime:
                logger.info(f'Upload timeout, {maxtime}s expired.')
                raise Exception("Upload Timeout")

            dataset_info = dataset_client.show_dataset(dataset_id)
            state = dataset_info['state']
            
            if state in {"ok", "empty", "error", "discarded", "failed_metadata"}:
                if state != "ok":
                    logger.warning(f"Dataset {dataset_id} is in terminal state {state}")
                    logger.error(f"Upload of Dataset {dataset_id} failed")
                    break
                logger.info(f"Dataset {dataset_id} is in non-terminal state {state}")

            if state in {'ok', 'error', 'failed'}:
                logger.info(f'Upload elapsed time: {elapsed_time}s')
                break
            
            time.sleep(interval)



def create_history(gi: GalaxyInstance, history_name: str = "Pulsar Endpoints Test", clean_histories=False) -> str:
    # Delete all histories to ensure there's enough free space
    if clean_histories:
        history_client = bioblend.galaxy.histories.HistoryClient(gi)
        for history in history_client.get_histories():
            history_client.delete_history(history['id'], purge=True)

    new_hist = gi.histories.create_history(name=history_name)
    logger.info(f'Creating History, ID: {new_hist["id"]}')

    return new_hist['id']



# Clean and Purge Histories from bioblend_test
def purge_histories(gi: GalaxyInstance) -> None:
    history_client = HistoryClient(gi)
    for history in history_client.get_histories():
        history_client.delete_history(history['id'], purge=True)
        logger.info(f'Purging History, ID: {history["id"]}',)
    


# Upload Workflow if old one is no more and get workflow id
def upload_workflow(gi: GalaxyInstance, wf_path: str ) -> str:
    wf = gi.workflows.import_workflow_from_local_path(wf_path)
    logger.info(f'Uploading Workflow, local path: {wf_path}')
    return wf['id']



# Delete Workflows 
def purge_workflow(gi: GalaxyInstance, workflow_id: str ) -> None:
    gi.workflows.delete_workflow(workflow_id)
    logger.info(f'Purging Workflow, ID: {workflow_id}')



# It returns a dict with the status
def monitor_job_status(gi: GalaxyInstance, invocation_id: str, start_time: datetime, 
                      timeout: int, sleep_time: int = SLEEP_TIME) -> dict:
    job_state = ''
    
    while True:
        # Check timeout
        elapsed_time = (datetime.now() - start_time).total_seconds()
        if elapsed_time + sleep_time > timeout:
            logger.info(f'Timeout {timeout}s expired.')
            return None

        # We don't do DDoSs in here.
        # Very mindfull
        # Very demure    
        time.sleep(sleep_time)
        
        # Get job status
        jobs = gi.jobs.get_jobs(invocation_id=invocation_id)
        if not jobs:
            continue
            
        current_job = jobs[0]
        
        # Log any state changes
        if job_state != current_job['state']:
            job_state = current_job['state']
            logger.info(f'    {job_state}')

            if job_state == "error":
                logger.info('The job encountered an error.')
                return None
            
        # Continue monitoring
        if current_job['exit_code'] is None:
            continue
            
        return current_job



def handle_job_completion(gi: GalaxyInstance, job: dict) -> int:
    # Cancel job if it's still running
    if job and job['state'] in ['new', 'queued', 'running']:
        logger.info('Canceling test job, timeout.')
        gi.jobs.cancel_job(job['id'])
        return 1
        
    # Handle completion
    if job and job['exit_code'] == 0:
        logger.info('Test job succeeded')
        gi.jobs.cancel_job(job['id'])
        return 0
        
    # Handle failure
    job_exit_code = job['exit_code'] if job and job['exit_code'] is not None else 'None'
    logger.info(f'Test job failed (exit_code: {job_exit_code})')
    gi.jobs.cancel_job(job['id'])
    return 1



def execute_and_monitor_workflow(gi: GalaxyInstance, workflow_id: str, 
                               workflow_input: dict, timeout: int, ID_history: str) -> int:
    start_time = datetime.now()
    
    # Workflow invocation
    invocation = gi.workflows.invoke_workflow(
        workflow_id,
        inputs=workflow_input,
        history_id= ID_history,
        history_name= "Compute testing"

    )
    logger.info( f'Invocation id: {invocation["id"]}')
    
    # Monitor the job using the previous function!
    logger.info('Waiting until test job finishes. Current state:')
    final_job_status = monitor_job_status(
        gi, invocation['id'], start_time, timeout
    )
    
    # Handle timeout case
    if final_job_status is None:
        return 1
        
    # Handle job completion
    return handle_job_completion(gi, final_job_status)



# Pretty sure this is need some fixing
def switch_pulsar(gi: GalaxyInstance, p_endpoint: str, name: str ) -> None:
    user_id = gi.users.get_current_user()['id']
    #prefs = gi.users.get_current_user()['preferences']['extra_user_preferences']
    prefs = gi.users.get_current_user().get('preferences', {}).get('extra_user_preferences', {})
    new_prefs = json.loads(prefs).copy() # TODO: find a workaround to not use the json library only for this bit
    new_prefs.update({'distributed_compute|remote_resources' : p_endpoint})

    if prefs != new_prefs:
        logger.info('Updating pulsar endpoint in user preferences')
        gi.users.update_user(user_id=user_id, user_data = new_prefs)
        if p_endpoint == "None":
            p_endpoint = "Default"
        logger.update_log_context( name, p_endpoint)
        logger.info(f"Testing pulsar endpoint {p_endpoint} "
                    f"from {name} instance")



def priority_vars(instance: dict, key_instance: str, conf: dict):
    if key_instance in instance and instance[key_instance] is not None:
        return instance[key_instance]
    return conf.get(key_instance)


def main():
    global logger
    exit_code = 0
    useg = ''
    logger = CustomLogger()
    logger.info("Starting...")
    config = load_config()

    def pvars(key: str):
        return priority_vars(useg, key, config)

    for i in range(len(config['usegalaxy_instances'])):
        try:    

            useg = config['usegalaxy_instances'][i]
            wf_path = pvars('ga_path')
            inputs_data = pvars('data_inputs')

            galaxy_instance = GalaxyInstance(url=useg['url'], key=useg['api'])
            logger.update_log_context(useg['name'], 'TBD')

            switch_pulsar(galaxy_instance, useg['default_compute_id'], name=useg['name'])
            id_hist = create_history(galaxy_instance)
            wfid = upload_workflow(galaxy_instance, wf_path)
            input = upload_and_build_data(galaxy_instance, id_hist, wfid, inputs_data, useg.get('maxwait'))

            for pe in useg['endpoints']:
                switch_pulsar(galaxy_instance, pe, name=useg['name'])
                exit_code = exit_code + execute_and_monitor_workflow(
                    gi = galaxy_instance,
                    workflow_id = wfid,
                    workflow_input = input,
                    timeout = pvars('timeout'),
                    ID_history = id_hist
                )
            logger.info("Cleaning Up...")
            purge_histories(galaxy_instance)
            purge_workflow(galaxy_instance, wfid)
            logger.info("Test completed")

        except KeyboardInterrupt:
            logger.warning("Test interrupted")
            purge_histories(galaxy_instance)
            purge_workflow(galaxy_instance, wfid)
            logger.info("Clean-up terminated")
            print("\n")
            sys.exit(exit_code)

        except bioblend.TimeoutException:
            logger.info("Timeout error")    

        except Exception as e:
            logger.warning(f"Error: {e}")
            purge_histories(galaxy_instance)
            purge_workflow(galaxy_instance, wfid)
            logger.info("Clean-up terminated")
            if i == len(config['usegalaxy_instances'])-1:
                logger.warning("Exiting with error")
                sys.exit(exit_code + 1)
            logger.warning("Skipping to the next instance")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
