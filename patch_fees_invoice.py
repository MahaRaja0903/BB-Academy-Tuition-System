import re

def patch_file(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    replacement = """{% set months = [] %}
{% for d in doc.fees_details %}
    {% if d.month and d.month not in months %}
        {% set _ = months.append(d.month) %}
    {% endif %}
{% endfor %}
{{ months | join(', ') }}"""
    
    new_content = content.replace("{{ doc.fee_month }}", replacement)

    with open(filepath, 'w') as f:
        f.write(new_content)

patch_file("bb_tution_management/fees_invoice.html")
patch_file("bb_tution_management/create_print_formats.py")
