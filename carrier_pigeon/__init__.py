import logging

from django.db import models as django_models
from django.db.models.signals import post_save
from django.db.models.signals import class_prepared

REGISTRY = {}


from carrier_pigeon.select import select

from carrier_pigeon.models import BasicDirtyFieldsMixin


def register(clazz):
    """Register a class as a push content configuration"""
    logger = logging.getLogger('carrier_pigeon.registry')
    name = clazz.__name__.lower()
    logger.debug('Registring ``%s`` rule.' % name)
    REGISTRY[name] = clazz()


def subscribe_to_post_save(sender, **kwargs):
    if BasicDirtyFieldsMixin in sender.mro():
        logger = logging.getLogger('carrier_pigeon.init')
        msg = 'Subscribing post_save for %s model' % sender._meta.object_name
        logger.debug(msg)
        post_save.connect(select, sender=sender)

class_prepared.connect(subscribe_to_post_save)
