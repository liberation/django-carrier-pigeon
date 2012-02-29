# -*- coding:utf-8 -*-

import shutil
import datetime

from carrier_pigeon.configuration import ZIPPusherConfiguration
from carrier_pigeon.linkers import StandardBinaryLinker

from example_app.models import Story

class WeeklyDigest(ZIPPusherConfiguration, StandardBinaryLinker):
    """
    Run `./manage.py pigeon_mass_push weeklydigest` to test it.
    """

    EXPORT_BINARIES = True

    def get_items_to_push(self):
        """ Export all articles published during the previous week. """

        now = datetime.datetime.now()
        one_week_ago = now - datetime.timedelta(days=7)
        items = Story.objects.filter(updating_date__gt=one_week_ago)
        return items
