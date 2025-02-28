#!/usr/bin/env python3

from src.logger import os
from src. secure_config import tempfile, Path
from src.bioblend_testjobs import json


def html_output(path: str, saber_results: dict) -> None:
    from jinja2 import Template

    script_dir = os.path.dirname(os.path.abspath(__file__))
    template_path = os.path.join(script_dir, 'templates', 'galaxy_template.html.j2')

    with open(template_path, 'r') as f:
        template_str = f.read()

    template = Template(template_str)

    # Render 
    rendered_html = template.render(data=saber_results)

    # Write to a file
    try:
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_file.write(rendered_html)
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
                f.write(rendered_html)
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
