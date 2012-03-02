# -*- coding:utf-8 -*-

import shutil
import datetime

from carrier_pigeon.configuration import ZIPPusherConfiguration
from carrier_pigeon.supervisors import BaseSupervisor
from carrier_pigeon.output_makers import TemplateOutputMaker, BinaryOutputMaker

from example_app.models import Story, Photo


class WeeklyDigestStorySupervisor(BaseSupervisor):

    def get_related_items(self):
        return [self.instance.photo]

    def get_output_makers(self):
        return [TemplateOutputMaker(self.configuration, self.instance)]
        

class WeeklyDigestPhotoSupervisor(BaseSupervisor):

    def get_output_makers(self):
        return [BinaryOutputMaker(self.configuration, self.instance, "original_file")]


class WeeklyDigest(ZIPPusherConfiguration):
    """
    Run `./manage.py pigeon_mass_push weeklydigest` to test it.
    """

    def get_supervisor_for_item(self, item):
        if item.__class__ == Story:
            return WeeklyDigestStorySupervisor(self, item)
        elif item.__class__ == Photo:
            return WeeklyDigestPhotoSupervisor(self, item)
        else:
            ValueError("No supervisor found for class %s" % item.__class__)

    def get_items_to_push(self):
        """ Export all articles published during the previous week. """

        now = datetime.datetime.now()
        one_week_ago = now - datetime.timedelta(days=7)
        items = Story.objects.filter(updating_date__gt=one_week_ago)
        return items

