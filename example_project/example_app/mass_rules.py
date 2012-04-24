# -*- coding:utf-8 -*-

import shutil
import datetime

from carrier_pigeon.configuration import MassPusherConfiguration
from carrier_pigeon.supervisors import BaseSupervisor
from carrier_pigeon.output_makers import TemplateOutputMaker, BinaryOutputMaker
from carrier_pigeon.packers import ZIPPacker, FlatPacker

from example_app.models import Story, Photo

class WeeklyDigestPhotoOutputMaker(BinaryOutputMaker):
    """
    Responsible of creating the output for a Photo.
    """

    @property
    def relative_final_directory(self):
        return 'photos'

    @property
    def final_file_name(self):
        return "%d.jpg" % self.instance.pk

class WeeklyDigestStorySupervisor(BaseSupervisor):

    def get_related_items(self):
        return [self.instance.photo]

    def get_output_makers(self):
        return [TemplateOutputMaker(self.configuration, self.instance)]
        

class WeeklyDigestPhotoSupervisor(BaseSupervisor):

    def get_output_makers(self):
        return [WeeklyDigestPhotoOutputMaker(self.configuration, self.instance, "original_file")]


class WeeklyDigest(MassPusherConfiguration):
    """
    Run `./manage.py pigeon_mass_push weeklydigest` to test it.
    """

    packer = ZIPPacker

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

class FlatMassExport(MassPusherConfiguration):
    """
    Run `./manage.py pigeon_mass_push weeklydigest` to test it.
    """

    packer = FlatPacker

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

