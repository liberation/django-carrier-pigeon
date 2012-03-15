# -*- coding:utf-8 -*-

import logging

from django.db.models.signals import post_save
from django.db.models.signals import class_prepared
from django.conf import settings

from carrier_pigeon.select import select
from carrier_pigeon.models import BasicDirtyFieldsMixin


def subscribe_to_post_save(sender, **kwargs):
    if BasicDirtyFieldsMixin in sender.mro():
        logger = logging.getLogger('carrier_pigeon.init')
        msg = 'Subscribing post_save for %s model' % sender._meta.object_name
        logger.debug(msg)
        post_save.connect(select, sender=sender)


if hasattr(settings, 'CARRIER_PIGEON_CLASSES'):

    # --- If there are no classes, carrier_pigeon is not really used by
    #      the project so we do not need to connect the post_save signal

    class_prepared.connect(subscribe_to_post_save)
