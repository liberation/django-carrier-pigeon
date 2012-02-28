# -*- coding: utf-8 -*-

from datetime import datetime

from carrier_pigeon.facility import add_item_to_push
from carrier_pigeon.validators import wellformed_xml_validator
from carrier_pigeon.configuration import SequentialPusherConfiguration

from models import Story


class BelovedPartnerPhoto(SequentialPusherConfiguration):
    def filter_by_instance_type(self, instance):
        return instance._meta.object_name == 'Photo'

    def filter_by_updates(self, instance):
        # We want all the photos in the queue
        return True

    def filter_by_state(self, instance):
        # We want all the photos in the queue
        return True

    def get_directory(self, instance):
        # Local directory in the working dir of pigeon
        return 'medias'

    def get_output_filename(self, instance):
        return "%d.jpg" % instance.pk

    def output(self, instance):
        return instance.original_file.file.read()


class BelovedPartner(SequentialPusherConfiguration):
    validators = (wellformed_xml_validator,)

    def filter_by_instance_type(self, instance):
        return instance._meta.object_name == "Story"

    def filter_by_updates(self, instance):
        # Candidates are Story that have these fields modified at current save
        to_check = ["workflow_state", "updating_date"]
        if any(field in instance._modified_attrs for field in to_check):
            return True
        return False

    def filter_by_state(self, instance):
        # WARNING : put the lightest tests before

        # We only want online stories
        if not instance.workflow_state == instance.WORKFLOW_STATE.ONLINE:
            return False

        # Minimum length of text is 500
        if len(instance.content) < 500:
            return False
        return True

    def get_extra_context(self, instance):
        read_also = Story.objects.all()[:3]  # Yes, ugly :)
        return {"read_also": read_also,}

    def get_output_filename(self, instance):
        return 'NEWS_%s_%d.xml' % (instance._meta.app_label.lower(), instance.pk)

    def post_select(self, instance):
        if instance.photo:
            # Queue the linked photo
            add_item_to_push(instance.photo, 'belovedpartnerphoto')
