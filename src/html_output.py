#!/usr/bin/env python3

from src.logger import os
from src. secure_config import tempfile, Path
from src.bioblend_testjobs import json


def html_output(path: str, saber_results: dict) -> None:
    from jinja2 import Template

    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templates', 'galaxy_template.html.j2')
    table_path = os.path.join(script_dir, 'templates', 'table_summary.html.j2')

    with open(template_path, 'r') as f:
        template_str = f.read()

    with open(table_path, 'r') as f:
        template_table_str = f.read()

    table_template = Template(template_table_str)
    template = Template(template_str)

    endpoint_counts = {}
    compute_data = saber_results
    # Parse the data structure
    for available_at, endpoints_data in compute_data.items():
        for endpoint, jobs_data in endpoints_data.items():
            job_types = ["SUCCESSFUL_JOBS", "FAILED_JOBS", "TIMEOUT_JOBS"]
            for job_type in job_types:
                if hasattr(jobs_data, job_type) and isinstance(getattr(jobs_data, job_type), dict):
                    jobs = getattr(jobs_data, job_type)
                elif isinstance(jobs_data, dict) and job_type in jobs_data:
                    jobs = jobs_data[job_type]
                else:
                    continue
                    
                for job_id in jobs:
                    key = (endpoint, available_at)
                    
                    if key not in endpoint_counts:
                        endpoint_counts[key] = 0
                        
                    endpoint_counts[key] += 1

    template_context = {
        "compute_data": compute_data,
        "endpoint_counts": endpoint_counts
    }


    # Render 
    rendered_html = table_template.render(**template_context, standalone=False)
    page_rendered_html = template.render(data=saber_results, rendered_html=rendered_html)


    # Write to a file
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_file.write(page_rendered_html)
            tmp_file.flush()  # Ensure data is written
            os.fsync(tmp_file.fileno())  # Force write to disk
            tmp_path = Path(tmp_file.name)
        
        os.replace(tmp_path, path) # Either succed or fails to replace file 
        print(f"HTML generated successfully as {path}")

    except OSError:
        # Fallback: Use same-directory temporary file
        temp_path = path.with_suffix('.tmp')
        try:
            # Write encrypted data to temporary file
            with open(temp_path, 'w') as f:
                f.write(page_rendered_html)
                f.flush()
                os.fsync(f.fileno())
            
            os.rename(temp_path, path)  # Still atomic like replace
            print(f"HTML generated successfully as {path}")
        except Exception as e:
            # Clean up
            if temp_path.exists():
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
            raise e
