#!/usr/bin/env python3

import sys
from src.logger import CustomLogger
from src.bioblend_testjobs import GalaxyTest
import yaml


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

        useg = dict(config['usegalaxy_instances'][i])
        copyconf = config.copy()
        copyconf.pop("usegalaxy_instances", None)
        useg.update(useg | copyconf )
        wf_path = pvars('ga_path')


        galaxy_instance = GalaxyTest(useg['url'], useg['api'], useg, logger)

        try:
            id_hist = galaxy_instance.create_history()
            wfid = galaxy_instance.upload_workflow()
            input = galaxy_instance.upload_and_build_data(id_hist, wfid)

            for pe in useg['endpoints']:
                galaxy_instance.switch_pulsar(pe)
                exit_code += galaxy_instance.execute_and_monitor_workflow(
                    workflow_id = wfid,
                    workflow_input = input,
                    ID_history = id_hist
                )
            logger.info("Cleaning Up...")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow(wfid)
            logger.info("Test completed")

        except KeyboardInterrupt:
            logger.warning("Test interrupted")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow(wfid)
            logger.info("Clean-up terminated")
            print("\n")
            sys.exit(exit_code)


        except Exception as e:
            logger.warning(f"Error: {e}")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow(wfid)
            logger.info("Clean-up terminated")
            if i == len(config['usegalaxy_instances'])-1:
                logger.warning("Exiting with error")
                sys.exit(exit_code + 1)
            logger.warning("Skipping to the next instance")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
