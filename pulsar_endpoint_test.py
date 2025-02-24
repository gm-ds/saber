#!/usr/bin/env python3

import sys
from src.globals import TOOL_NAME, PATH_EXIT, P
from src.logger import CustomLogger
from src.secure_config import SecureConfig
from src.bioblend_testjobs import GalaxyTest



def main():
    exit_code = 0
    useg = ''
    logger = CustomLogger()
    logger.info("Starting...")

    try:
        safe_config = SecureConfig(TOOL_NAME)
        safe_config.initialize_encryption(P)
        
    except (ValueError, PermissionError) as e:
        logger.error(f"An error occurred: {e}")
        sys.exit(PATH_EXIT)

    config = safe_config.load_config()

    for i in range(len(config['usegalaxy_instances'])):

        useg = dict(config['usegalaxy_instances'][i])
        copyconf = config.copy()
        copyconf.pop("usegalaxy_instances", None)
        useg.update(useg | copyconf )

        galaxy_instance = GalaxyTest(useg['url'], useg['api'], useg.get('email', None),
                                      useg.get('password', None), useg, logger)

        try:
            input = galaxy_instance.test_job_set_up()

            for pe in useg['endpoints']:
                galaxy_instance.switch_pulsar(pe)
                exit_code += galaxy_instance.execute_and_monitor_workflow(
                    workflow_input = input
                )
            logger.info("Cleaning Up...")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow()
            galaxy_instance.switch_pulsar(useg['default_compute_id'])
            logger.info("Test completed")

        except KeyboardInterrupt:
            logger.warning("Test interrupted")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow()
            logger.info("Clean-up terminated")
            print("\n")
            sys.exit(exit_code)


        except Exception as e:
            logger.warning(f"Error: {e}")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow()
            logger.info("Clean-up terminated")
            if i == len(config['usegalaxy_instances'])-1:
                logger.warning("Exiting with error")
                sys.exit(exit_code + 1)
            logger.warning("Skipping to the next instance")
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
