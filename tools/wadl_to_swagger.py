#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals

import os
from os import path
import xml.sax
import logging
from copy import copy
import json

log = logging.getLogger(__file__)

TYPE_MAP = {
    'string': 'string',
    'xsd:string': 'string',
    'csapi:string': 'string',
    'xsd:int': 'integer',
    'csapi:uuid': 'string',
    'xsd:boolean': 'boolean',
    'boolean': 'boolean',
    'object': 'object',
    'csapi:bool': 'boolean',
    'xsd:bool': 'boolean',
    'xsd:datetime': 'string',
    'regexp': 'string',
    'xsd:datetime': 'string',
    'xsd:dict': 'object',
    'alarm': 'string',
    'xsd:timestamp': 'string',
    'xsd:char': 'string',
    'list': 'array',
    'csapi:flavorswithonlyidsnameslinks': 'string',
    'csapi:imagestatus': 'string',
    'csapi:imageswithonlyidsnameslinks': 'string',
    'xsd:enum': 'string',
    'xsd:anyuri': 'string',
    'csapi:serverforupdate': 'string',
    'string': 'string',
    'imageapi:string': 'string',
    'imageapi:imagestatus': 'string',
    'imageapi:uuid': 'string',
    'csapi:uuid': 'string',
    'csapi:serverforcreate': 'string',
    'csapi:blockdevicemapping': 'string',
    'csapi:serverswithonlyidsnameslinks': 'string',
    'csapi:serverstatus': 'string',
    'csapi:dict': 'object',
    'imageforcreate': 'string',
    'xsd:ip': 'string',

    # TODO This array types also set the items
         # "tags": {
         #    "type": "array",
         #    "items": {
         #        "type": "string"
    'xsd:list': 'array',
    'array': 'array',
}

FORMAT_MAP = {
    'xsd:anyURI': 'uri',
    'xsd:datetime': 'date-time',
    'xsd:ip': 'ipv4',
    'regexp': 'regexp',
    'xsd:timestamp': 'timestamp',
}

STYLE_MAP = {
    'template': 'path',
    'plain': 'body',
    'query': 'query',
    'header': 'header',
}

MIME_MAP = {
    'json': 'application/json',
    'txt': 'text/plain',
    'xml': 'application/xml',
}


def create_parameter(name, _in, description='',
                     type='xsd:string', required=True):
    return {
        "name": name,
        "in": STYLE_MAP[_in],
        "description": description,
        "required": True if required == 'true' else False,
        "type": TYPE_MAP[type.lower()],
        "format": FORMAT_MAP.get(type, ''),
    }


class SubParser(object):
    def __init__(self, parent):
        # general state
        self.tag_stack = []
        self.attr_stack = []
        self.content = None
        self.parent = parent
        self.result = None

    def startElement(self, name, _attrs):
        attrs = dict(_attrs)
        self.tag_stack.append(name)
        self.attr_stack.append(attrs)
        return attrs

    def endElement(self, name):
        self.tag_stack.pop()
        self.attr_stack.pop()
        if not self.tag_stack:
            self.parent.detach_subparser(self.result)


class ParaParser(SubParser):
    def __init__(self, parent):
        super(ParaParser, self).__init__(parent)
        self.content = []

    def startElement(self, name, _attrs):
        super(ParaParser, self).startElement(name, _attrs)

    def endElement(self, name):
        content = ''.join(self.content)
        self.result = content
        super(ParaParser, self).endElement(name)

    def characters(self, content):
        if not content:
            return
        if content[0] == '\n':
            return
        if content[0] == ' ':
            content = ' ' + content.lstrip()
        if self.tag_stack[-1] == 'code':
            self.content.append('`' + content + '`')
        else:
            self.content.append(content)


class ContentHandler(xml.sax.ContentHandler):

    def __init__(self, filename):
        self.filename = filename

    def startDocument(self):
        # API state
        self.apis = {}
        self.current_api = None

        # Resource Mapping
        self.resource_map = {}
        self.resource_types = {}

        # URL paths
        self.url_map = {}
        self.url_params = {}
        self.url = []

        # general state
        self.tag_stack = []
        self.attr_stack = []
        self.content = None
        self.parser = None

        # metadata
        self.info = {}
        self.global_tags = []

    def detach_subparser(self, result):
        self.parser = None
        self.result_fn(result)
        self.result_fn = None

    def attach_subparser(self, parser, result_fn):
        self.parser = parser
        self.result_fn = result_fn

    def endDocument(self):
        for api in self.apis.values():
            for method in api:
                method['consumes'] = list(method['consumes'])
                method['produces'] = list(method['produces'])

    def parameter_description(self, content):
        name = self.attr_stack[-2]['name']
        self.url_params[name] = content

    def api_summary(self, content):
        self.current_api['summary'] = content

    def request_parameter_description(self, content):
        self.current_api['parameters'][-1]['description'] = content

    def response_schema_description(self, content):
        status_code = self.attr_stack[-4]['status']
        self.current_api['responses'][status_code]['schema']['items'][-1]['description'] = content

    def search_stack_for(self, tag_name):
        for tag, attrs in zip(reversed(self.tag_stack),
                              reversed(self.attr_stack)):
            if tag == tag_name:
                return attrs

    def on_top_tag_stack(self, *args):
        return self.tag_stack[-len(args):] == list(args)

    def startElement(self, name, _attrs):
        if name == 'para':
            if self.on_top_tag_stack('resource', 'param', 'wadl:doc'):
                self.attach_subparser(ParaParser(self),
                                      self.parameter_description)
            if self.on_top_tag_stack('method', 'wadl:doc'):
                self.attach_subparser(ParaParser(self), self.api_summary)

            if self.on_top_tag_stack('request', 'representation',
                                     'param', 'wadl:doc'):
                self.attach_subparser(ParaParser(self),
                                      self.request_parameter_description)
            if self.on_top_tag_stack('response', 'representation', 'param',
                                     'wadl:doc'):
                self.attach_subparser(ParaParser(self),
                                      self.response_schema_description)

        if self.parser:
            return self.parser.startElement(name, _attrs)

        attrs = dict(_attrs)
        self.tag_stack.append(name)
        self.attr_stack.append(attrs)
        self.content = []
        if name == 'method':
            if 'id' in attrs and 'name' in attrs:
                id = attrs['id']
                if id in self.url_map:
                    url = self.url_map[id]
                elif id in self.resource_map:
                    resource = self.resource_map[id]
                    url = self.resource_types[resource]
                else:
                    raise Exception("Can't find method.")
                name = attrs['name'].lower()
                if url in self.apis:
                    root_api = self.apis[url]
                else:
                    self.apis[url] = root_api = []
                self.current_api = {
                    'tags': copy(self.global_tags),
                    'method': name,
                    'produces': set(),
                    'consumes': set(),
                    'parameters': [],
                    'responses': {},
                }
                root_api.append(self.current_api)

                for param, doc in self.url_params.items():
                    if ('{%s}' % param) in url:
                        self.current_api['parameters'].append(
                            create_parameter(param, 'template', doc))
        # Info
        if name == 'resources':
            self.info['section'] = attrs['xml:id']
        # URL paths
        if name == 'resource':
            self.url.append(attrs.get('path', '/')[
                int(attrs.get('path', '/').startswith('//')):])
        if self.tag_stack[-2:] == ['resource_type', 'method']:
            self.resource_map[attrs.get('href').strip('#')] \
                = self.attr_stack[-2]['id']

        # Methods and Resource Types
        if self.on_top_tag_stack('application', 'resource'):
            self.global_tags.append(attrs['id'])
        if name == 'resource' and attrs.get('type'):
            self.resource_types[attrs.get('type').strip('#')] \
                = '/'.join(self.url)
        if self.on_top_tag_stack('resource', 'method'):
            self.url_map[attrs.get('href').strip('#')] = '/'.join(self.url)

        if self.on_top_tag_stack('method', 'wadl:doc'):
            self.current_api['title'] = attrs.get('title')
        if name == 'xsdxt:code':
            if not attrs.get('href'):
                return
            if self.tag_stack[-4] == 'request':
                type = 'request'
            else:
                type = 'response'
                status_code = self.search_stack_for('response')['status']
            media_type = MIME_MAP[attrs['href'].rsplit('.', 1)[-1]]

            pathname = path.join(path.dirname(self.filename), attrs['href'])
            try:
                sample = open(pathname).read()
                if media_type == 'application/json':
                    sample = json.loads(sample)
            except IOError:
                log.warning("Can't find file %s" % pathname)
                sample = None

            self.current_api['produces'].add(media_type)
            self.current_api['consumes'].add(media_type)
            if sample and type == 'response':
                response = self.current_api['responses'][status_code]
                if 'examples' not in response:
                    response['examples'] = {}
                response['examples'][media_type] = sample

        if name == 'response':
            if 'status' not in attrs:
                return
            status_code = attrs['status']
            self.current_api['responses'][status_code] = {}

        if self.on_top_tag_stack('request', 'representation', 'param'):
            name = attrs['name']
            self.current_api['parameters'].append(
                create_parameter(
                    name=name,
                    _in=attrs.get('style', 'plain'),
                    description='',
                    type=attrs.get('type', 'string'),
                    required=attrs.get('required')))
        if self.on_top_tag_stack('response', 'representation', 'param'):
            status_code = self.attr_stack[-3]['status']
            name = attrs['name']
            if 'schema' not in self.current_api['responses'][status_code]:
                self.current_api['responses'][status_code]['schema'] = {
                    'items': [],
                }
            self.current_api['responses'][status_code]['schema']['items'].append(
                create_parameter(
                    name=name,
                    _in=attrs.get('style', 'plain'),
                    description='',
                    type=attrs.get('type', 'string'),
                    required=attrs.get('required')))

    def endElement(self, name):
        if self.parser:
            return self.parser.endElement(name)

        content = ' '.join(self.content)

        # URL paths
        if name == 'resource':
            self.url.pop()

        self.tag_stack.pop()
        self.attr_stack.pop()

    def characters(self, content):
        if self.parser:
            return self.parser.characters(content)

        content = content.strip()
        if content:
            self.content.append(content)

    def processingInstruction(self, target, data):
        print(target)
        pass

    def ignorableWhitespace(self, whitespace):
        pass

    def skippedEntity(self, name):
        pass

    def startPrefixMapping(self, prefix, uri):
        pass

    def endPrefixMapping(self, prefix):
        pass

    def setDocumentLocator(self, locator):
        pass


def main(source_file, output_dir, service_name):
    log.info('Parsing %s' % source_file)
    ch = ContentHandler(source_file)
    xml.sax.parse(source_file, ch)
    os.chdir(output_dir)
    output = {
        u'info': ch.info,
        u'paths': ch.apis,
        u'schemes': {},
        u'tags': {},
        u'basePath': {},
        u'securityDefinitions': {},
        u'host': {},
        u'definitions': {},
        u'swagger': {},
        u'externalDocs': {},
        u"swagger": u"2.0",
    }
    pathname = '%s-%s-swagger.json' % (service_name, ch.info['section'])
    with open(pathname, 'w') as out_file:
        json.dump(output, out_file, indent=2, sort_keys=True)


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
    reducing_path = filename
    head = True
    while head:
        head, tail = path.split(reducing_path)
        if tail == 'src' or tail == 'xsd':
            os.chdir(head)
            break
        reducing_path = head
    service = path.split(path.split(reducing_path)[0])[1]
    main(filename, output_dir=current_dir, service_name=service)
