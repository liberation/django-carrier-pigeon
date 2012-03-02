# -*- coding:utf-8 -*-

import logging

from django.db.models.signals import post_save
from django.db.models.signals import class_prepared
from django.conf import settings

from carrier_pigeon.select import select
from carrier_pigeon.models import BasicDirtyFieldsMixin
from carrier_pigeon.utils import get_instance


REGISTRY = {}


def add_instance(instance, clazz_path=None):
    global REGISTRY
    REGISTRY[instance.name] = instance
    logger = logging.getLogger('carrier_pigeon.init')
    msg = 'Registered %s' % clazz_path if clazz_path is not None \
            else instance.__class__.__name__.lower()
    logger.debug(msg)


def register_config(clazz_path):
    instance = get_instance(clazz_path)
    add_instance(instance, clazz_path)


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

    for clazz_module in settings.CARRIER_PIGEON_CLASSES:
        register_config(clazz_module)
