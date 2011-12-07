# -*- coding:utf-8 -*-

import os
import pickle
import hashlib
import logging

from contextlib import closing
from urlparse import urlparse
from zipfile import ZipFile, ZIP_DEFLATED

from django.db.models import fields

from models import ItemToPush


logger = logging.getLogger('carrier_pigeon.utils')


class URL:
    """ Represents an url with information extracted so that it's easily
    accessible. """

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


class TreeHash:
    """ Allow to compute a validation hash for a whole directory tree.
    Used in local vs. remote testing. """

    def __init__(self, local_root):
        self._local_root = local_root
        self._files = list()
        self._hasher = hashlib.sha1
        self._hash = ''

    def hash_file(self, fn):
        hasher = self._hasher()
        with open(fn,'rb') as f: 
            for chunk in iter(lambda: f.read(128*hasher.block_size), ''): 
                 hasher.update(chunk)
        return hasher.hexdigest()

    def list_files(self):
        self._files = list()
        for root, dirs, files in os.walk(self._local_root, topdown=True):
            for f in files:
                fn_full = os.path.join(root, f)
                fn_rel = fn_full.replace(self._local_root, '.')
                self._files.append((
                    fn_rel,                   # file name, rel. to local root
                    os.stat(fn_full).st_size, # file size, in bytes
                    self.hash_file(fn_full),  # file hash
                ))

        #logging.debug(u"TreeHash.list_files(): %s" % str(self._files))

    def compute(self):
        self.list_files()
        digest = pickle.dumps(self._files)
        self._hash = self._hasher(digest).hexdigest()

        #logging.debug(u"TreeHash.compute(): %s" % self._hash)

        return self._hash

    def hash(self):
        return self._hash or self.compute()


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


# From: http://coreygoldberg.blogspot.com/2009/07/python-zip-directories-recursively.html
def zipdir(dir, zip_file):
    zip_ = ZipFile(zip_file, 'w', compression=ZIP_DEFLATED)
    root_len = len(os.path.abspath(dir))
    for root, dirs, files in os.walk(dir):
        archive_root = os.path.abspath(root)[root_len:]
        for f in files:
            fullpath = os.path.join(root, f)
            archive_name = os.path.join(archive_root, f)
            zip_.write(fullpath, archive_name, ZIP_DEFLATED)
    zip_.close()
