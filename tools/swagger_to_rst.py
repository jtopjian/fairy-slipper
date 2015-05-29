#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals

from os import path
import logging
import json

from jinja2 import Template

log = logging.getLogger(__file__)

TMPL_TXT = """
{% for path, requests in swagger['paths'].items() -%}
{% for method, attributes in requests.items() -%}
{% for status_code, attributes in requests.items() -%}


{{attributes.title}}
{{ "=" * attributes.title|length }}

.. http:{{method}}:: {{path}}

   {{attributes.summary}}
{% for parameter in attributes.parameters -%}
{% if parameter.in == 'path' %}
   :parameter {{parameter.name}}: {{parameter.description}}
{%- elif parameter.in == 'query' %}
   :query {{parameter.name}}: {{parameter.description}}
{%- endif %}
{%- endfor %}

{% endfor -%}
{% endfor -%}
{% endfor -%}
"""
TMPL = Template(TMPL_TXT)


def main(filename):
    swagger = json.load(open(filename))
    print(TMPL.render(swagger=swagger))


if '__main__' == __name__:
    import argparse

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    parser.add_argument(
        'filename',
        help="File to convert")

    args = parser.parse_args()

    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(name)s %(levelname)s %(message)s')

    filename = path.abspath(args.filename)

    main(filename)
