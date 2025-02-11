#!/usr/bin/env python3

import sys
import time
import configparser
import logging
import json
import bioblend
from datetime import datetime
from bioblend.galaxy import GalaxyInstance
from bioblend.galaxy.histories import HistoryClient


SLEEP_TIME = 5

# Logging set up
def setup_logging():
    logging.basicConfig(
        filename="/home/ubuntu/saber/testrun.log",
        #filename="/var/log/py_pulsar_test_telegraf.log",
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.INFO,
        datefmt='%Y-%m-%d %H:%M:%S'
    )



# Loading Config using json list
def load_config(config_path='pulsar_test.ini'):
    try:
        with open(config_path, 'r') as f:
            config = configparser.ConfigParser()
            config.read_file(f)
            
        return {
            'galaxy_url': config['DEFAULT']['GalaxyUrl'],
            'galaxy_api_key': config['DEFAULT']['GalaxyAPIKey'],
            'workflow_path': config['DEFAULT']['WorkflowPath'],
            'workflow_input_path': config['DEFAULT']['WorkflowInput'],
            'hist_name' : config['DEFAULT']['HistoryName'],
            'pulsar_endpoint': json.loads(config['DEFAULT']['PulsarEndpoint']),
            'timeout': int(config['DEFAULT']['Timeout'])
        }
    except (FileNotFoundError, PermissionError) as e:
        logging.error(f"Error reading {config_path}: {e}")
        sys.exit(1)

# Upload necessary data
def upload_and_build_data(gi, history_id: str, workflow_id: str, inputs_path: str) -> dict:
    with open(inputs_path, 'r') as f:
        inputs_dict = json.load(f)
    data = dict()
    for file_name, file_options in inputs_dict.items():
        file_url = file_options['url']
        file_type = file_options['file_type']
        upload = gi.tools.put_url(file_url, history_id=history_id, file_name=file_name, file_type=file_type)
        upload_id = upload['outputs'][0]['id']
        wf_input = gi.workflows.get_workflow_inputs(workflow_id, label=file_name)[0]
        data[wf_input] = {'id':upload_id, 'src':'hda'}

    # Wait for dataset
    wait_for_dataset(gi, history_id)

    return data


def wait_for_dataset(gi: GalaxyInstance, history_id: str) -> None:
    dataset_client = bioblend.galaxy.datasets.DatasetClient(gi)
    all_datasets = dataset_client.get_datasets(history_id=history_id)
    for dataset in all_datasets:
        dataset_client.wait_for_dataset(dataset['id'])
# TODO: Different timeout for uploading! 

def create_history(gi: GalaxyInstance, history_name: str, clean_histories=False) -> str:
    # Delete all histories to ensure there's enough free space
    if clean_histories:
        history_client = bioblend.galaxy.histories.HistoryClient(gi)
        for history in history_client.get_histories():
            history_client.delete_history(history['id'], purge=True)

    new_hist = gi.histories.create_history(name=history_name)

    return new_hist['id']


# Clean and Purge Histories from bioblend_test
def purge_histories(gi: GalaxyInstance) -> None:
    history_client = HistoryClient(gi)
    for history in history_client.get_histories():
        history_client.delete_history(history['id'], purge=True)
    


# Upload Workflow if old one is no more and get workflow id
def upload_workflow(gi: GalaxyInstance, wf_path: str ) -> str:
    wf = gi.workflows.import_workflow_from_local_path(wf_path)
    return wf['id']



# Delete Workflows 
def purge_workflow(gi: GalaxyInstance, workflow_id: str ) -> None:
    gi.workflows.delete_workflow(workflow_id)



# It returns a dict with the status
def monitor_job_status(gi: GalaxyInstance, invocation_id: str, start_time: datetime, 
                      timeout: int, sleep_time: int = SLEEP_TIME) -> dict:
    job_state = ''
    
    while True:
        # Check timeout
        elapsed_time = (datetime.now() - start_time).total_seconds()
        if elapsed_time + SLEEP_TIME > timeout:
            logging.info(f'Timeout {timeout}s expired.')
            return None

        # We don't do DDoSs in here.
        # Very mindfull
        # Very demure    
        time.sleep(SLEEP_TIME)
        
        # Get job status
        jobs = gi.jobs.get_jobs(invocation_id=invocation_id)
        if not jobs:
            continue
            
        current_job = jobs[0]
        
        # Log any state changes
        if job_state != current_job['state']:
            job_state = current_job['state']
            logging.info(f'    {job_state}')

            if job_state == "error":
                logging.error('The job encountered an error.')
                return None
            
        # Continue monitoring
        if current_job['exit_code'] is None:
            continue
            
        return current_job



def handle_job_completion(gi: GalaxyInstance, job: dict) -> int:
    # Cancel job if it's still running
    if job and job['state'] in ['new', 'queued', 'running']:
        logging.info('Canceling test job, timeout.')
        gi.jobs.cancel_job(job['id'])
        return 1
        
    # Handle completion
    if job and job['exit_code'] == 0:
        logging.info('Test job succeeded')
        gi.jobs.cancel_job(job['id'])
        return 0
        
    # Handle failure
    job_exit_code = job['exit_code'] if job and job['exit_code'] is not None else 'None'
    logging.info(f'Test job failed (exit_code: {job_exit_code})')
    gi.jobs.cancel_job(job['id'])
    return 1



def execute_and_monitor_workflow(gi: GalaxyInstance, workflow_id: str, 
                               workflow_input: dict, timeout: int, ID_history: str, Name_history: str) -> int:
    start_time = datetime.now()
    
    # Workflow invocation
    invocation = gi.workflows.invoke_workflow(
        workflow_id,
        inputs=workflow_input,
        history_id= ID_history,
        history_name= Name_history # type: ignore

    )
    logging.info(f'Invocation id: {invocation["id"]}')
    
    # Monitor the job using the previous function!
    logging.info('Waiting until test job finishes. Current state:')
    final_job_status = monitor_job_status(
        gi, invocation['id'], start_time, timeout
    )
    
    # Handle timeout case
    if final_job_status is None:
        return 1
        
    # Handle job completion
    return handle_job_completion(gi, final_job_status)


# Pretty sure this is need some fixing
def switch_pulsar(gi: GalaxyInstance, p_endpoint: str, url: str ) -> None:
    user_id = gi.users.get_current_user()['id']
    #prefs = gi.users.get_current_user()['preferences']['extra_user_preferences']
    prefs = gi.users.get_current_user().get('preferences', {}).get('extra_user_preferences', {})
    new_prefs = json.loads(prefs).copy()
    new_prefs.update({'distributed_compute|remote_resources' : p_endpoint})

    if prefs != new_prefs:
        logging.info('Updating pulsar endpoint in user preferences')
        gi.users.update_user(user_id=user_id, user_data = new_prefs)
        logging.info(f"Testing pulsar endpoint {p_endpoint} "
                    f"using Galaxy server at {url}")



def main():
    exit_code = 0
    setup_logging()
    config = load_config()
    hist_name = config['hist_name']
    wf_path = config['workflow_path']
    inputs_path = config['workflow_input_path']

    galaxy_instance = GalaxyInstance(url=config['galaxy_url'], key=config['galaxy_api_key'])

    try:
        switch_pulsar(galaxy_instance, "None", url=config['galaxy_url'])
        id_hist = create_history(galaxy_instance, hist_name)
        wfid = upload_workflow(galaxy_instance, wf_path)
        input = upload_and_build_data(galaxy_instance, id_hist, wfid, inputs_path)

        for pe in config['pulsar_endpoint']:
            switch_pulsar(galaxy_instance, pe, url=config['galaxy_url'])
            exit_code = exit_code + execute_and_monitor_workflow(
                gi = galaxy_instance,  # Fixed variable reference
                workflow_id = wfid,
                workflow_input = input,
                timeout = config['timeout'],
                ID_history = id_hist,
                Name_history= hist_name
            )
        sys.exit(exit_code)

    except KeyboardInterrupt:
        logging.info("Test interrupted")
        print("\nScript terminated")
    
    finally:
        purge_histories(galaxy_instance)
        purge_workflow(galaxy_instance, wfid)


if __name__ == '__main__':
    main()
