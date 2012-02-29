# -*- coding:utf-8 -*-

import logging

from abc import abstractmethod
from datetime import datetime

from django.conf import settings
from django.template import Context
from django.template import loader
from django.template.base import TemplateDoesNotExist

from carrier_pigeon import REGISTRY

from models import ItemToPush
from facility import add_item_to_push
from senders import DefaultSender, FTPSender
from utils import URL, TreeHash, join_url_to_directory, zipdir, \
    is_file_field, is_relation_field, related_objects


logger = logging.getLogger('carrier_pigeon.linkers')


class BaseBinaryLinker():

    def item_binaries(self, item, depth):
        """ Return the list of binary files linked to this item, by
        listing file-like fields on this item and its related ones.
        Should be implemented in a Linker module. """

        return list()

    def output_binaries(self, item):
        """ Output all `item`'s linked binaries. Return file list.
        Should be implemented in a Linker module. """

        return list()


class StandardBinaryLinker(BaseBinaryLinker):

    # --- OVERRIDE US! :)

    # --- Should the linked binaries be exported as well?
    EXPORT_BINARIES = False
    # --- If so, should we only export binaries in certain fields? (None=ALL)
    EXPORT_BINARIES_FIELDS = None
    # --- Should we look for binaries across relationships?
    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = False
    # --- If so, across how many relationship levels?
    EXPORT_BINARIES_RELATIONSHIP_DEPTH = 0

    def item_binaries(self, item, depth):
        """ Return the list of binary files linked to this item, by
        listing file-like fields on this item and its related ones. """

        binaries = list()
        try:
            fields = item._meta.fields
        except:
            return binaries

        for field in fields:

            # --- If this is a "File-like" field, get the file path
            if is_file_field(field):
                if field.name in self.EXPORT_BINARIES_FIELDS or \
                    not self.EXPORT_BINARIES_FIELDS:
                    binaries.append(field.path)

            # --- If this is a "Relation-like" field, recurse
            elif is_relation_field(field) and depth:
                for obj in related_objects(item, field):
                    binaries.extend(self.item_binaries(obj, depth-1))

        return binaries

    def output_binaries(self, item):
        """ Output all `item`'s linked binaries, according to the 
        EXPORT_BINARIES, EXPORT_BINARIES_ACROSS_RELATIONSHIPS and
        EXPORT_BINARIES_RELATIONSHIP_DEPTH settings. Return file list. """

        if not self.EXPORT_BINARIES:
            return list()

        depth = self.EXPORT_BINARIES_RELATIONSHIP_DEPTH \
            if self.EXPORT_BINARIES_ACROSS_RELATIONSHIPS else 0

        return self.item_binaries(item, depth)
