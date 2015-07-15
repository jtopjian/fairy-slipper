# -*- mode: python -*-
import os
from pecan.deploy import deploy
pathname = os.path.join(os.path.abspath(os.dirname(__file__)), 'config.py')
application = deploy(pathname)
