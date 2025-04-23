#!/usr/bin/env python3

import sys


def print_example():
    from src.globals import example
    print(example)
    sys.exit(0)



def main():
    from datetime import timedelta
    from src.logger import CustomLogger
    from src.args import Parser, datetime
    from src.secure_config import SecureConfig
    from src.bioblend_testjobs import GalaxyTest, json, ConnectionError, WFPathError
    from src.globals import TOOL_NAME, P, CONFIG_PATH, ERR_CODES


    results = dict()
    conn_rr = False
    exc = False

    try:
        args = Parser(P, CONFIG_PATH).arguments()

        logger = CustomLogger(TOOL_NAME, args.log_dir)
        logger.info("Starting...")

        if args.example_settings:
            print_example()
            sys.exit(0)

            
        # Manage -cryption and edit flags and ops
        # TODO: tests!!!!!
        if args.encrypt:
            safe_config = SecureConfig(TOOL_NAME, args.encrypt)
            safe_config.initialize_encryption(args.password)
            safe_config.encrypt_existing_file()
            logger.info(f"File encrypted: {args.encrypt}")
            sys.exit(0)
        
        elif args.decrypt:
            safe_config = SecureConfig(TOOL_NAME, args.decrypt)
            safe_config.initialize_encryption(args.password)
            safe_config.decrypt_existing_file()
            logger.info(f"File decrypted: {args.decrypt}")
            sys.exit(0)
            
        elif args.edit:
            safe_config = SecureConfig(TOOL_NAME, args.edit)
            safe_config.initialize_encryption(args.password)
            safe_config.edit_config()
            sys.exit(0)
            


        # Initialize secure configuration
        if args.settings is None:
            safe_config = SecureConfig(TOOL_NAME)
            safe_config.initialize_encryption(args.password)
        else:
            safe_config = SecureConfig(TOOL_NAME, args.settings)
            safe_config.initialize_encryption(args.password)

            
    except (ValueError, PermissionError) as e:
        logger.error(f"An error occurred with configuration: {e}")
        sys.exit(ERR_CODES['path'])

    try:
        config = safe_config.load_config()
        config["config_path"] = str(safe_config.get_config_path())

        if args.html_report or args.table_html_report or args.md_report:
            start_dt = datetime.now()
            start_d = start_dt.strftime("%b %d, %Y %H:%M")
            string = config.get("date_string", False)
            config["date"] = {"sDATETIME": start_d, "nDATETIME": string}

    
        for i in range(len(config['usegalaxy_instances'])):

            useg = dict(config['usegalaxy_instances'][i])
            copyconf = config.copy()
            copyconf.pop("usegalaxy_instances", None)
            copyconf.update(useg)
            useg = copyconf

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

            except WFPathError as e:
                logger.error(e)
                logger.warning(f"Exiting with error: {ERR_CODES['path']}")
                galaxy_instance.clean_up()
                sys.exit(ERR_CODES['path'])
            except Exception as e:
                exc = True
                logger.warning(f"Error: {e}")
                galaxy_instance.clean_up()
                if not i == len(config['usegalaxy_instances'])-1:
                    logger.warning("Skipping to the next instance")
                continue
            except ConnectionError as e:
                conn_rr = True
                logger.warning(f"Connection Error while testing {useg['name']}:")
                logger.warning(f"{e}")
                galaxy_instance.clean_up()
                if not i == len(config['usegalaxy_instances'])-1:
                    logger.warning("Skipping to the next instance")
                continue

            for pe in useg['endpoints']:
                try:
                    galaxy_instance.switch_pulsar(pe)
                    compute_id = pe if pe != 'None' else 'Default'

                    if useg['name'] not in results:
                        results[useg['name']] = {}

                    if compute_id not in results[useg['name']]:
                        results[useg['name']][compute_id] = {
                            "SUCCESSFUL_JOBS": {}, 
                            "RUNNING_JOBS": {},
                            "QUEUED_JOBS": {},
                            "NEW_JOBS": {},
                            "WAITING_JOBS": {},
                            "FAILED_JOBS": {}
                        }

                    pre_results = galaxy_instance.execute_and_monitor_workflow(
                        workflow_input = input
                        )
                    for key in ["SUCCESSFUL_JOBS", "RUNNING_JOBS", "FAILED_JOBS", "WAITING_JOBS", "QUEUED_JOBS", "NEW_JOBS"]:
                        if key in pre_results and isinstance(pre_results[key], dict):
                            results[useg['name']][compute_id][key].update(pre_results[key])

                except Exception as e:
                    logger.warning(f"An error occurred while testing {pe}:")
                    logger.warning(f"{e}")
                    logger.warning("Continuing...")

                except ConnectionError as e:
                    logger.warning(f"A Connection error occurred while testing {pe}:")
                    logger.warning(f"{e}")
                    logger.warning("Continuing...")
                    
            try:    
                galaxy_instance.clean_up()
                galaxy_instance.switch_pulsar(useg['default_compute_id'])

            except Exception as e:
                logger.warning(f"An error occurred while cleaning up:")
                logger.warning(f"{e}")
                logger.warning("Continuing...")

            except ConnectionError as e:
                logger.warning(f"An error occurred while cleaning up:")
                logger.warning(f"{e}")
                logger.warning("Continuing...")

        try:
            if args.html_report:
                from src.html_output import Report
                report = Report(args.html_report, results, config, class_logger=logger)
                report.output_page()

            if args.md_report:
                from src.html_output import Report
                report = Report(args.md_report, results, config, class_logger=logger)
                report.output_md()


            if args.table_html_report:
                from src.html_output import Report
                summary = Report(args.table_html_report, results, config, class_logger=logger)
                summary.output_summary(True)

        except Exception:
            logger.warning("The reports might not have been generated.")

        print(json.dumps(results, indent=2, sort_keys=False)) #Work In Progress

        logger.info("Test completed")

        for g_name, g_data in results.items():
            for com_id, job_data in g_data.items():
                for k in ["RUNNING_JOBS","WAITING_JOBS", "QUEUED_JOBS", "NEW_JOBS"]:
                    if job_data.get(k):
                        logger.warning(f"Uncompleted jobs found in {g_name}/{com_id}.")
                        logger.warning(f"Exiting with code: {ERR_CODES['tto']}")
                        if not conn_rr or not exc:
                            sys.exit(ERR_CODES['tto'])
                if job_data.get("FAILED_JOBS"):
                    logger.warning(f"Failed jobs found in {g_name}/{com_id}.")
                    logger.warning(f"Exiting with code: {ERR_CODES['job']}")
                    if not conn_rr or not exc:
                        sys.exit(ERR_CODES['job'])
        if conn_rr:
            sys.exit(ERR_CODES['api'])
        if exc:
            sys.exit(ERR_CODES['gal'])     
        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("Test interrupted")
        galaxy_instance.clean_up()
        print("\n")
        sys.exit(0)

if __name__ == '__main__':
    main()
