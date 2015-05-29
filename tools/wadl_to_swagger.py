#!/usr/bin/env python
from __future__ import print_function
from __future__ import unicode_literals

import os
from os import path
import xml.sax
import logging
import json

log = logging.getLogger(__file__)

TYPE_MAP = {
    'xsd:string': 'string',
    'csapi:string': 'string',
    'xsd:int': 'integer',
    'csapi:uuid': 'string',
    'xsd:boolean': 'boolean',
    'xsd:datetime': 'string',
    'xsd:dict': 'object',
    'string': 'string',
}

FORMAT_MAP = {
}

STYLE_MAP = {
    'template': 'path',
    'plain': 'body',
    'query': 'query',

}


def create_parameter(name, _in, description='',
                     type='xsd:string', required=True):
    return {
        "name": name,
        "in": STYLE_MAP[_in],
        "description": description,
        "required": True if required == 'true' else False,
        "type": TYPE_MAP[type],
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

        # URL paths
        if name == 'resource':
            self.url.append(attrs.get('path')[
                int(attrs.get('path').startswith('//')):])
        if self.tag_stack[-2:] == ['resource_type', 'method']:
            self.resource_map[attrs.get('href').strip('#')] = self.attr_stack[-2]['id']
        ## Methods and Resource Types
        if name == 'resource' and attrs.get('type'):
            self.resource_types[attrs.get('type').strip('#')] = '/'.join(self.url)
        if self.tag_stack[-2:] == ['resource', 'method']:
            self.url_map[attrs.get('href').strip('#')] = '/'.join(self.url)

        if self.tag_stack[-2:] == ['method', 'wadl:doc']:
            self.current_api['title'] = attrs.get('title')
        if name == 'xsdxt:code':
            if not attrs.get('href'):
                return
            if self.tag_stack[-4] == 'request':
                type = 'request'
            else:
                type = 'response'
                status_code = self.attr_stack[-4]['status']
            media_type = self.attr_stack[-3]['mediaType']
            os.chdir(path.dirname(self.filename))
            sample = open(attrs['href']).read()
            if media_type == 'application/json':
                sample = json.loads(sample)

            self.current_api['produces'].add(media_type)
            self.current_api['consumes'].add(media_type)
            if type == 'response':
                self.current_api['responses'][status_code] = response = {}
                if 'examples' not in response:
                    response['examples'] = {}
                response['examples'][media_type] = sample

        if self.tag_stack[-3:] == ['request', 'representation', 'param']:
            name = attrs['name']
            self.current_api['parameters'].append(
                create_parameter(
                    name=name,
                    _in=attrs['style'],
                    description='',
                    type=attrs['type'],
                    required=attrs['required']))
        if self.tag_stack[-3:] == ['response', 'representation', 'param']:
            status_code = self.attr_stack[-3]['status']
            name = attrs['name']
            if 'schema' not in self.current_api['responses'][status_code]:
                self.current_api['responses'][status_code]['schema'] = {
                    'items': [],
                }
            self.current_api['responses'][status_code]['schema']['items'].append(
                create_parameter(
                    name=name,
                    _in=attrs['style'],
                    description='',
                    type=attrs['type'],
                    required=attrs['required']))

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


def main(source_file, output_dir):
    ch = ContentHandler(source_file)
    xml.sax.parse(source_file, ch)
    os.chdir(output_dir)
    output = {
        u'info': {},
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
    with open('swagger.json', 'w') as out_file:
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
        if tail == 'src':
            os.chdir(head)
            break
        reducing_path = head
    main(filename, output_dir=current_dir)
