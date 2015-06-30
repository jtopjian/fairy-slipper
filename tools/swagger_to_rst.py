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

TMPL_API = """
{%- for path, requests in swagger['paths'].items() -%}
{%- for request in requests -%}

{{request.summary}}
{{ "=" * request.summary|length }}

.. http:{{request.method}}:: {{path}}

{{request.description|wrap}}
{% if request['examples']['application/json'] %}
   :swagger-request: {{version}}/examples/{{request['id']}}_req.json
{%- endif -%}
{% for status_code, response in request.responses.items() -%}
{%- if response['examples']['application/json'] %}
   :swagger-response {{status_code}}: {{version}}/examples/{{request['id']}}_resp_{{status_code}}.json
{%- endif -%}
{% endfor -%}
{% for tag in request.tags %}
   :swagger-tag: {{tag}}
{%- endfor -%}
{% for parameter in request.parameters -%}
{% if parameter.in == 'body' -%}
{% if parameter.schema %}
   :swagger-schema: {{version}}/{{request['id']}}.json
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

TMPL_TAG = """
{%- for tag in swagger.tags -%}
{{tag.description}}
{{ "=" * tag.description|length }}

.. swagger:tag:: {{tag.name}}
{{tag.summary|wrap}}

{% endfor %}
"""
environment = Environment()


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
    write_examples(swagger, output_dir)


def write_rst(swagger, output_dir):
    environment.extend(swagger_info=swagger['info'])
    write_apis(swagger, output_dir)
    write_tags(swagger, output_dir)


def write_apis(swagger, output_dir):
    info = swagger['info']
    version = info['version']
    service = info['service']
    service_path = path.join(output_dir, service)
    output_file = '%s.rst' % version
    if not path.exists(service_path):
        os.makedirs(service_path)
    TMPL = environment.from_string(TMPL_API)
    result = TMPL.render(swagger=swagger,
                         version=swagger['info']['version'])
    filepath = path.join(service_path, output_file)
    log.info("Writing APIs %s", filepath)
    with codecs.open(filepath,
                     'w', "utf-8") as out_file:
        out_file.write(result)


def write_tags(swagger, output_dir):
    info = swagger['info']
    version = info['version']
    service = info['service']
    service_path = path.join(output_dir, service)
    if not path.exists(service_path):
        os.makedirs(service_path)
    output_file = '%s-tags.rst' % version
    TMPL = environment.from_string(TMPL_TAG)
    result = TMPL.render(swagger=swagger,
                         version=swagger['info']['version'])
    filepath = path.join(service_path, output_file)
    log.info("Writing Tags %s", filepath)
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


def write_examples(swagger, output_dir):
    info = swagger['info']
    version = info['version']
    service = info['service']
    service_path = path.join(output_dir, service)
    versioned_path = path.join(service_path, version)
    full_path = path.join(versioned_path, 'examples')
    if not path.exists(service_path):
        os.makedirs(service_path)
    if not path.exists(versioned_path):
        os.makedirs(versioned_path)
    if not path.exists(full_path):
        os.makedirs(full_path)

    for operations in swagger['paths'].values():
        for operation in operations:
            if 'examples' in operation:
                for mime, example in operation['examples'].items():
                    filename = '%s' % '_'.join([operation['id'], 'req'])
                    if mime == 'application/json':
                        filepath = path.join(full_path, filename + '.json')
                        log.info("Writing %s", filepath)
                        file = open(filepath, 'w')
                        json.dump(example, file, indent=2)
                    if mime == 'text/plain':
                        filepath = path.join(full_path, filename + '.txt')
                        log.info("Writing %s", filepath)
                        example = example.strip()
                        example = example + '\n'
                        file = open(filepath, 'w')
                        file.write(example)
            for status_code, response in operation['responses'].items():
                for mime, example in response['examples'].items():
                    filename = '%s' % '_'.join([operation['id'],
                                                'resp',
                                                status_code])
                    if mime == 'application/json':
                        filepath = path.join(full_path, filename + '.json')
                        log.info("Writing %s", filepath)
                        file = open(filepath, 'w')
                        json.dump(example, file, indent=2)
                    if mime == 'text/plain':
                        filepath = path.join(full_path, filename + '.txt')
                        log.info("Writing %s", filepath)
                        example = example.strip()
                        example = example + '\n'
                        file = open(filepath, 'w')
                        file.write(example)


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
