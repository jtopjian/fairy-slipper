#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals

import os
from os import path
import logging
import json
import codecs
import textwrap

from jinja2 import Template

log = logging.getLogger(__file__)

TMPL_TXT = """
{% for path, requests in swagger['paths'].items() -%}
{% for request in requests -%}

{{request.summary}}
{{ "=" * request.summary|length }}

.. http:{{request.method}}:: {{path}}

{{wrap(request.description)}}
{% for parameter in request.parameters -%}
{% if parameter.in == 'path' %}
   :parameter {{parameter.name}}: {{parameter.description}}
{%- elif parameter.in == 'query' %}
   :query {{parameter.name}}: {{parameter.description}}
{%- endif %}
{%- endfor %}

{% endfor -%}
{% endfor -%}
"""
TMPL = Template(TMPL_TXT)


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


def main(filename, output_dir):
    log.info('Parsing %s' % filename)
    swagger = json.load(open(filename))
    output_file = path.basename(filename).rsplit('.', 1)[0] + '.rst'
    result = TMPL.render(swagger=swagger, wrap=wrapper)
    with codecs.open(path.join(output_dir, output_file),
                     'w', "utf-8") as out_file:
        out_file.write(result)


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
