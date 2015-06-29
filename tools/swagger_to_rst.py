#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals

import os
from os import path
import logging
import json
import codecs
import textwrap

from jinja2 import Environment, environmentfilter

log = logging.getLogger(__file__)

TMPL_TXT = """
{%- for path, requests in swagger['paths'].items() -%}
{%- for request in requests -%}

{{request.summary}}
{{ "=" * request.summary|length }}

.. http:{{request.method}}:: {{path}}

{{request.description|wrap}}
{% if request['examples']['application/json'] %}
   **Example request**

   .. sourcecode:: http

{{request['examples']['application/json']|format_json}}
{% endif -%}
{% for status_code, response in request.responses.items() -%}
{%- if response['examples']['application/json'] %}
   **Example response**

   .. sourcecode:: http

{{response['examples']['application/json']|format_json}}
{% endif -%}
{% endfor -%}
{% for parameter in request.parameters -%}
{% if parameter.in == 'body' %}
{% if parameter.schema %}
   :swagger-schema {{parameter.schema['$ref']|schema_path}}: {{parameter.description}}
{%- endif -%}
{% elif parameter.in == 'path' %}
   :parameter {{parameter.name}}: {{parameter.description}}
{%- elif parameter.in == 'query' %}
   :query {{parameter.name}}: {{parameter.description}}
{%- endif %}
{%- endfor -%}
{% for status_code, response in request.responses.items() %}
   :response {{status_code}}: {{response.description}}
{%- endfor %}


{% endfor %}
{%- endfor %}
"""
environment = Environment()


def format_json(obj):
    string = json.dumps(obj, indent=2)
    return '\n'.join(['      ' + line for line in string.split('\n')])

environment.filters['format_json'] = format_json


@environmentfilter
def schema_path(env, obj):
    service = env.swagger_info['service']
    version = env.swagger_info['version']
    schema_name = obj.rsplit('/', 1)[-1]
    return '/'.join([service, version, schema_name])

environment.filters['schema_path'] = schema_path


def wrapper(string):
    wrap = textwrap.TextWrapper(initial_indent='   ',
                                subsequent_indent='   ')
    bullet_wrap = textwrap.TextWrapper(initial_indent='   - ',
                                       subsequent_indent='     ')
    new_text = []
    for line in string.split('\n'):
        if line.startswith('-'):
            new_text.extend(bullet_wrap.wrap(line[1:].strip()))
        else:
            new_text.append('')  # newline here, because magic
            new_text.extend(wrap.wrap(line.strip()))

    return '\n'.join(new_text)

environment.filters['wrap'] = wrapper


def main(filename, output_dir):
    log.info('Parsing %s' % filename)
    swagger = json.load(open(filename))
    write_rst(swagger, output_dir)
    write_jsonschema(swagger, output_dir)


def write_rst(swagger, output_dir):
    output_file = path.basename(filename).rsplit('.', 1)[0] + '.rst'
    environment.extend(swagger_info=swagger['info'])
    TMPL = environment.from_string(TMPL_TXT)
    result = TMPL.render(swagger=swagger)
    filepath = path.join(output_dir, output_file)
    log.info("Writing %s", filepath)
    with codecs.open(filepath,
                     'w', "utf-8") as out_file:
        out_file.write(result)


def write_jsonschema(swagger, output_dir):
    info = swagger['info']
    version = info['version']
    service = info['service']
    service_path = path.join(output_dir, service)
    full_path = path.join(service_path, version)
    if not path.exists(service_path):
        os.makedirs(service_path)
    if not path.exists(full_path):
        os.makedirs(full_path)

    for schema_name, schema in swagger['definitions'].items():
        filename = '%s.json' % schema_name
        filepath = path.join(full_path, filename)
        log.info("Writing %s", filepath)
        file = open(filepath, 'w')
        json.dump(schema, file, indent=2)


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

    current_dir = os.getcwd()
    main(filename, output_dir=current_dir)
