#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals

from os import path
import logging
import json

log = logging.getLogger(__file__)


def main(filename):
    swagger = json.load(open(filename))
    for uri, info in swagger['paths'].items():
        for endpoint in info:
            for i, response in enumerate(endpoint['responses'].items()):
                status_code, resp_info = response

                if 'parameters' not in endpoint:
                    continue

                schema = {parameter['name']: parameter
                          for parameter in endpoint['parameters']
                          if parameter['in'] == 'body'}
                if not schema:
                    continue

                for item in schema.values():
                    del item['name']
                    if '_in' in item:
                        del item['_in']

                file = open(''.join([uri.replace('/', '_'),
                                     '-',
                                     str(i),
                                     '-request-schema.json']), 'w')
                json.dump({'type': 'object',
                           'properties': schema},
                          file,
                          indent=2)


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
