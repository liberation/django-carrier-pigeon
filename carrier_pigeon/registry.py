# -*- coding:utf-8 -*-

import logging

from django.conf import settings

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


if hasattr(settings, 'CARRIER_PIGEON_CLASSES'):

    for clazz_module in settings.CARRIER_PIGEON_CLASSES:
        register_config(clazz_module)
