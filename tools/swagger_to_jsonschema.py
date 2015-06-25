#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals

from copy import copy
from os import path
import urllib
import logging
import json

log = logging.getLogger(__file__)


def main(swagger_filename):
    log.info("Processing file %s", swagger_filename)
    swagger = json.load(open(swagger_filename))
    info = swagger['info']
    service_name = info['service_name']
    section = info['section']
    version = info['version']
    for uri, info in swagger['paths'].items():
        for i, endpoint in enumerate(info):
            for response in endpoint['responses'].items():
                status_code, resp_info = response

                if 'parameters' not in endpoint:
                    continue

                # Skip any status codes above the 200s without any
                # return value.
                if int(status_code.split()[0]) >= 300 and not resp_info:
                    continue

                try:
                    schema = {parameter['name']: copy(parameter)
                              for parameter in endpoint['parameters']
                              if parameter['in'] == 'body'}
                except Exception:
                    import pdb; pdb.set_trace()  # FIXME
                if not schema:
                    continue

                for item in schema.values():
                    del item['name']
                    if '_in' in item:
                        del item['_in']
                filename = ''.join([service_name, '-',
                                    version, '-',
                                    section, '-',
                                    'schema-request-',
                                    urllib.quote(uri, ''),
                                    '-',
                                     str(i),
                                    '.json'])
                if path.exists(filename):
                    import pdb; pdb.set_trace()  # FIXME

                assert not path.exists(filename), "Filename %s exists" % filename
                file = open(filename, 'w')
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
