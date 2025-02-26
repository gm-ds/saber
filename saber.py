#!/usr/bin/env python3

import sys


def print_example():
    from src.globals import example
    print(example)
    sys.exit(0)



def main():
    from src.args import Parser
    from src.logger import CustomLogger
    from src.secure_config import SecureConfig
    from src.bioblend_testjobs import GalaxyTest, json
    from src.globals import TOOL_NAME, PATH_EXIT, TIMEOUT_EXIT, GAL_ERROR, JOB_ERR_EXIT, P, CONFIG_PATH


    results = dict()
    logger = CustomLogger(TOOL_NAME)
    logger.info("Starting...")


    try:
        args = Parser(P, CONFIG_PATH).arguments()

        if args.example_settings:
            print_example()
            sys.exit(0)

            
        # Initialize secure configuration
        safe_config = SecureConfig(TOOL_NAME)
        safe_config.initialize_encryption(args.password)
        
        # Manage -cryption and edit flags and ops
        # TODO: tests!!!!!
        if args.encrypt:
            safe_config = SecureConfig(TOOL_NAME, args.encrypt)
            safe_config.initialize_encryption(args.password)
            safe_config.encrypt_existing_file()
            logger.info(f"File encrypted: {args.encrypt}")
            sys.exit(0)
        
        if args.decrypt:
            safe_config = SecureConfig(TOOL_NAME, args.decrypt)
            safe_config.initialize_encryption(args.password)
            safe_config.decrypt_existing_file()
            logger.info(f"File decrypted: {args.decrypt}")
            sys.exit(0)
            
        if args.edit:
            safe_config = SecureConfig(TOOL_NAME, args.edit)
            safe_config.initialize_encryption(args.password)
            safe_config.edit_config()
            sys.exit(0)
            
        if args.settings:
            safe_config = SecureConfig(TOOL_NAME, args.settings)
            safe_config.initialize_encryption(args.password)
            
    except (ValueError, PermissionError) as e:
        logger.error(f"An error occurred with configuration: {e}")
        sys.exit(PATH_EXIT)


    config = safe_config.load_config()
    config["config_path"] = safe_config.get_config_path()

    for i in range(len(config['usegalaxy_instances'])):

        useg = dict(config['usegalaxy_instances'][i])
        copyconf = config.copy()
        copyconf.pop("usegalaxy_instances", None)
        useg.update(useg | copyconf )

        galaxy_instance = GalaxyTest(
            useg['url'], 
            useg['api'], 
            useg.get('email', None), 
            useg.get('password', None), 
            useg, 
            logger
            )

        try:
            input = galaxy_instance.test_job_set_up()

            for pe in useg['endpoints']:
                galaxy_instance.switch_pulsar(pe)
                if useg['name'] not in results:
                    results[useg['name']] = {"SUCCESSFUL_JOBS": {}, "TIMEOUT_JOBS": {}, "FAILED_JOBS": {}}
                pre_results = galaxy_instance.execute_and_monitor_workflow(
                    workflow_input = input
                    )
                for key in ["SUCCESSFUL_JOBS", "TIMEOUT_JOBS", "FAILED_JOBS"]:
                    if key in pre_results and isinstance(pre_results[key], dict):
                        results[useg['name']][key].update(pre_results[key])  

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
            sys.exit(0)


        except Exception as e:
            logger.warning(f"Error: {e}")
            galaxy_instance.purge_histories()
            galaxy_instance.purge_workflow()
            logger.info("Clean-up terminated")
            if i == len(config['usegalaxy_instances'])-1:
                logger.warning("Exiting with error")
                sys.exit(GAL_ERROR)
            logger.warning("Skipping to the next instance")

    print(json.dumps(results, indent=2, sort_keys=False)) #Work In Progress
    for r in results.values():
        if r.get("TIMEOUT_JOBS"):
            logger.warning(f"At least one job reached timeout, exiting with: {TIMEOUT_EXIT}")
            sys.exit(TIMEOUT_EXIT)
        if r.get("FAILED_JOBS"):
            logger.warning(f"At least one job failed, exiting with: {JOB_ERR_EXIT}")
            sys.exit(JOB_ERR_EXIT)
    sys.exit(0)


if __name__ == '__main__':
    main()
