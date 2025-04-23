#!/usr/bin/env python3

from jinja2 import Template, TemplateError
from src.globals import TOOL_NAME
from src.logger import os, CustomLogger
from src. secure_config import tempfile, Path

class Report:
    def __init__(self, path: Path, dict_results: dict, configuration: dict, class_logger = None):
        self.logger = class_logger if isinstance(class_logger, CustomLogger) else  CustomLogger(TOOL_NAME)
        self.path = path
        self.saber_results = dict_results
        self.config = configuration

    def _write_file(self, content):
        try:
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()  # Ensure data is written
                os.fsync(tmp_file.fileno())  # Force write to disk
                tmp_path = Path(tmp_file.name)
            
            os.replace(tmp_path, self.path) # Either succed or fails to replace file 
            self.logger.info(f"Report generated successfully at {self.path}")

        except OSError:
            # Fallback: Use same-directory temporary file
            temp_path = self.path.with_suffix('.tmp')
            try:
                # Write encrypted data to temporary file
                with open(temp_path, 'w') as f:
                    f.write(content)
                    f.flush()
                    os.fsync(f.fileno())
                
                os.rename(temp_path, self.path)  # Still atomic like replace
                self.logger.info(f"Report generated successfully at {self.path}")
            except Exception as e:
                # Clean up
                self.logger.warning(f"An error occured while writing the report: {e}")
                if temp_path.exists():
                    try:
                        os.unlink(temp_path)
                        self.logger.warning(f"Temporary file {temp_path} removed after failure")
                    except Exception:
                         self.logger.warning(f"Failed to remove temporary file {temp_path}")
                raise e



    def _process_data(self) -> dict:
        endpoint_counts = {}
        instances_counts = {}
        urls = {}
        pies = {}
        compute_data = self.saber_results
        # Parse the data structure
        self.logger.info("Processing data...")
        for available_at, endpoints_data in compute_data.items():
            for endpoint, jobs_data in endpoints_data.items():
                job_types = ["SUCCESSFUL_JOBS", "RUNNING_JOBS", "FAILED_JOBS", "WAITING_JOBS", "QUEUED_JOBS", "NEW_JOBS"]

                instances_counts.setdefault(available_at, 0)
                instances_counts[available_at] += 1

                if available_at not in pies:
                    pies[available_at] = {}
                if endpoint not in pies[available_at]:
                    pies[available_at][endpoint] = {}
                    pies[available_at][endpoint]['tot'] = 0
                for k in job_types:
                    pies[available_at][endpoint]['tot'] += len(jobs_data.get(k, {}))
                if pies[available_at][endpoint]['tot'] > 0:
                    pies[available_at][endpoint]['bb_errors'] = False
                    for k in job_types:
                        key = k.split('_')[0].lower()  
                        pies[available_at][endpoint][key] = (len(jobs_data.get(k, {}))/pies[available_at][endpoint]['tot']) * 100
                else:
                    pies[available_at][endpoint]['bb_errors'] = True

                for job_type in job_types:
                    jobs = None
                    if hasattr(jobs_data, job_type) and isinstance(getattr(jobs_data, job_type), dict):
                        jobs = getattr(jobs_data, job_type)
                    elif isinstance(jobs_data, dict) and job_type in jobs_data:
                        jobs = jobs_data[job_type]
                        
                    if not jobs:
                        continue
                        
                    for job_id in jobs:
                        key = (endpoint, available_at)
                        endpoint_counts.setdefault(key, 0)
                        endpoint_counts[key] += 1


        for i in self.config['usegalaxy_instances']:
            urls[i['name']] = i['url']

        return {
            "compute_data": compute_data,
            "endpoint_counts": endpoint_counts,
            "instances_counts": instances_counts,
            "urls": urls,
            "cherry": pies
        }



    def output_page(self) -> None:

        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, 'templates', 'galaxy_template.html.j2')

        with open(template_path, 'r') as f:
            template_str = f.read()

        template = Template(template_str)

        # Render 
        try:
            rendered_html = self.output_summary(standalone=False)
            page_rendered_html = template.render(data=self.saber_results, rendered_html=rendered_html)
        except TemplateError as e:
            self.logger.error(f"Template rendering error: {str(e)}")
            raise
        
        self.logger.info("HTML page rendering completed.")
        self._write_file(page_rendered_html)



    def output_summary(self, standalone: bool):

        script_dir = os.path.dirname(os.path.abspath(__file__))
        table_path = os.path.join(script_dir, 'templates', 'table_summary.html.j2')

        with open(table_path, 'r') as f:
            template_table_str = f.read()

        table_template = Template(template_table_str)
        template_context = self._process_data()

        # Render
        try:
            rendered_html = table_template.render(**template_context, standalone=standalone, date=self.config["date"])
        except TemplateError as e:
            self.logger.error(f"Template rendering error: {str(e)}")
            raise


        if standalone:
            self.logger.info("HTML table rendering completed.")
            self._write_file(rendered_html)
        else:
            return rendered_html
        
    def output_md(self) -> None:

        script_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(script_dir, 'templates', 'galaxy_report.md.j2')

        with open(template_path, 'r') as f:
            template_str = f.read()

        template = Template(template_str)
        template_context = self._process_data()

        # Render 
        try:
            page_rendered_md = template.render(**template_context, data=self.saber_results,  date=self.config["date"])
        except TemplateError as e:
            self.logger.error(f"Template rendering error: {str(e)}")
            raise
        self.logger.info("Markdown file rendering completed.")

        self._write_file(page_rendered_md)