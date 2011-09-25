# -*- coding:utf-8 -*-

""" This should go in a project rather than here, but this is just a WIP. """

import datetime
from libe.models import Article
from carrier_pigeon.configuration import ArchivePusherConfiguration

class TestArchiveConfiguration(ArchivePusherConfiguration):

    def get_items_to_push(self):
        """ Export all articles published during the previous week. """

        now = datetime.datetime.now()
        one_week_ago = now - datetime.timedelta(days=7)
        items = Article.objects.filter(publication_date__gt=one_week_ago)
        return items
