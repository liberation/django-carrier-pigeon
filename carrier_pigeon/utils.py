# -*- coding:utf-8 -*-

import os
from contextlib import closing
from urlparse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED

from django.db.models import fields

from models import ItemToPush


class URL:
    """Represents an url with information extracted so that it's easly
    accessible"""

    def __init__(self, url):
        self.url = url
        parsed = urlparse(url)
        self.scheme = parsed.scheme
        self.path = parsed.path
        self.params = parsed.params
        self.query = parsed.query
        self.fragment = parsed.fragment

        if '@' in parsed.netloc:
            login_password, self.domain = parsed.netloc.split('@')
            self.login, self.password = login_password.split(':')
        else:
            self.domain = parsed.netloc
            self.login = self.password = None

        if ':' in self.domain:
            self.domain, self.port = self.domain.split(':')
        else:
            self.port = None


def join_url_to_directory(url, directory):
    ends_with = url.endswith('/')
    starts_with = directory.endswith('/')

    if ends_with and starts_with:
        return ''.join((url, directory[1:]))

    if ((ends_with and not starts_with) or
        (not ends_with and starts_with)):
        return ''.join((url, directory))

    if not ends_with and not starts_with:
        return ''.join((url, '/', directory))

    raise Exception('Unhandled case')


def duplicate_row(rule_name, instance):
    """Checks if there is already is a row like this one."""
    app_label = instance._meta.app_label
    model = instance._meta.module_name
    name = instance._meta.verbose_name
    id = instance.id

    query = ItemToPush.objects.filter(rule_name=rule_name,
                                      status=ItemToPush.STATUS.NEW,
                                      content_type__app_label=app_label,
                                      content_type__model=model,
                                      content_type__name=name,
                                      object_id=id)
    count = query.count()

    return count > 0


def get_instance(clazz_module):
    module_path = clazz_module.split('.')
    module_path, clazz_name = module_path[:-1], module_path[-1]
    module_path = '.'.join(module_path)
    module = __import__(module_path, globals(), locals(), [clazz_name], -1)
    instance = getattr(module, clazz_name)()
    return instance


def is_file_field(field):
    return fields.files.FileField in field.__class__.mro()

def is_relation_field(field):
    return fields.related.RelatedField in field.__class__.mro()

def related_objects(instance, field):
    f = getattr(instance, field.name)
    try:
        return f.all()
    except AttributeError:
        return [f]

# From: http://stackoverflow.com/questions/296499
def zipdir(base_dir, archive_name):
    with closing(ZipFile(archive_name, "w", ZIP_DEFLATED)) as zip_:
        for root, dirs, files in os.walk(base_dir):
            for filename in files:
                absolute_filename = os.path.join(root, filename)
                zip_filename = absolute_filename[len(base_dir)+len(os.sep):]
                zip_.write(absolute_filename, zip_filename)
