import os
import json
import itertools
from os import path

from pecan import expose
from pecan.core import redirect
from pecan import conf

from webob.exc import status_map


class DocController(object):

    def __init__(self, service_info):
        self.service_info = service_info

    @expose('json')
    def index(self):
        return self.service_info


class ServicesController(object):

    def __init__(self):
        filepath = path.join(conf.app.api_doc, 'index.json')
        self.services_info = json.load(open(filepath))
        self.url_map = {}
        for key, info in self.services_info.items():
            current_map = self.url_map
            previous_map = None
            for part in [k for k in key.split('/') if k]:
                if part not in current_map:
                    current_map[part] = {}
                previous_map = current_map
                current_map = current_map[part]
            else:
                previous_map[part] = DocController(info)

    @expose('json')
    def index(self):
        return self.services_info

    @expose('json')
    def _lookup(self, *components):
        url_map = self.url_map
        url_walk = itertools.chain(components)
        for component in url_walk:
            if component in url_map:
                url_map = url_map[component]
            else:
                break
            if isinstance(url_map, DocController):
                return url_map, [u for u in url_walk]


class RootController(object):

    @expose(generic=True, template='index.html')
    def index(self):
        return dict()

    @index.when(method='POST')
    def index_post(self, q):
        redirect('http://pecan.readthedocs.org/en/latest/search.html?q=%s' % q)

    @expose('error.html')
    def error(self, status):
        try:
            status = int(status)
        except ValueError:
            status = 0
        message = getattr(status_map.get(status), 'explanation', '')
        return dict(status=status, message=message)

    doc = ServicesController()
