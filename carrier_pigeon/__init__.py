import logging

from django.db import models as django_models
from django.db.models.signals import post_save
from django.db.models.signals import class_prepared
from django.conf import settings


REGISTRY = {}


from carrier_pigeon.select import select

from carrier_pigeon.models import BasicDirtyFieldsMixin


def register_config(clazz_module):
    global REGISTRY
    module_path = clazz_module.split('.')
    module_path, clazz_name = module_path[:-1], module_path[-1]
    module_path = '.'.join(module_path)
    module = __import__(module_path, globals(), locals(), [clazz_name], -1)
    instance = getattr(module, clazz_name)()
    REGISTRY[instance.name()] = instance
    logger = logging.getLogger('carrier_pigeon.init')
    msg = 'Registred %s configuration from %s' % (clazz_name, module_path)
    logger.debug(msg)


for clazz_module in settings.CARRIER_PIGEON_CLASSES:
    register_config(clazz_module)


def subscribe_to_post_save(sender, **kwargs):
    if BasicDirtyFieldsMixin in sender.mro():
        logger = logging.getLogger('carrier_pigeon.init')
        msg = 'Subscribing post_save for %s model' % sender._meta.object_name
        logger.debug(msg)
        post_save.connect(select, sender=sender)

class_prepared.connect(subscribe_to_post_save)
