#!/usr/bin/env python3

import sys
from src.globals import TOOL_NAME, PATH_EXIT
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
        safe_config.initialize_encryption('place_holder')
        
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
            id_hist = galaxy_instance.create_history()
            wfid = galaxy_instance.upload_workflow(safe_config.get_config_path())
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
