#!/usr/bin/env python
import os
from distutils.core import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    if os.path.exists(file_path):
        return open(file_path).read()
    else:
        return ''

setup(name='django-carrier-pigeon',
      version='0.0',
      description='Django application for managing asynchronous task queue',
      long_description=read('README.rst'),
      author='Djaz Team',
      author_email='devweb@liberation.fr',
      url='https://github.com/liberation/django-push-content',
      packages=['carrier_pigeon'],
     )
