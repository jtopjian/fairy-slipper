import os
import json
import logging
import itertools
from os import path

from pecan import expose
from pecan.core import redirect
from pecan import conf
from webob.exc import status_map
import docutils.core

from fairy_slipper.rest import JSONWriter
from fairy_slipper import hooks


logger = logging.getLogger(__name__)


class DocController(object):

    __hooks__ = [hooks.CORSHook()]

    def __init__(self, service_path, service_info):
        self.service_info = service_info
        base_filepath = path.join(conf.app.api_doc, service_path.rstrip('/'))
        self.api_rst = base_filepath + '.rst'
        self.tags_rst = base_filepath + '-tags.rst'
        if not path.exists(self.api_rst):
            logger.warning("Can't find ReST API doc at %s", self.api_rst)
        if not path.exists(self.tags_rst):
            logger.warning("Can't find ReST TAG doc at %s", self.tags_rst)

    @expose('json')
    def index(self):
        json = docutils.core.publish_file(
            open(self.api_rst),
            writer=JSONWriter())
        import pdb; pdb.set_trace()  # FIXME
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
                previous_map[part] = DocController(key, info)

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
