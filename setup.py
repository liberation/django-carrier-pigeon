#!/usr/bin/env python
from os import path
from distutils.core import setup

with open(path.join(path.dirname(__file__), 'README.rst')) as f:
    readmin = f.read()

setup(name='django-carrier-pigeon',
      version='0.1',
      description='Django application that help pushing content to remote locations',
      long_description=readme,
      author='Djaz Team',
      author_email='devweb@liberation.fr',
      url='https://github.com/liberation/django-push-content',
      packages=['carrier_pigeon'],
     )
