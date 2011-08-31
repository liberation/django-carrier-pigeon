"""
    ___init___
    ==========

    This module is used to initialize ``carrier_pigeon`` when the app is loaded.
    You should carefully add ``carrier_pigeon`` to the end of the ``INSTALLED_APPS``
    list settings.

"""
import logging

from django.db import models as django_models
from django.db.models.signals import post_save
from django.db.models.signals import class_prepared
from django.conf import settings

#: Stores configurations with their name as key, the name of a configuration can
#: be retrived through :data:`carrier_pigeon.configuration.DefaultConfiguration.name`
REGISTRY = {}


from carrier_pigeon.select import select
from carrier_pigeon.models import BasicDirtyFieldsMixin
from carrier_pigeon.utils import get_instance


def add_instance(instance, clazz_path=None):
    """Adds instance configuration to :data:`carrier_pigeon.REGISTRY`"""
    global REGISTRY
    REGISTRY[instance.name] = instance
    logger = logging.getLogger('carrier_pigeon.init')
    msg = 'Registred %s' % clazz_path if clazz_path is not None else instance.__class__.__name__.lower()
    logger.debug(msg)


def register_config(clazz_path):
    """Adds a configuration to :data:`carrier_pigeon.REGISTRY` from class path
        string ``clazz_path``"""
    instance = get_instance(clazz_path)
    add_instance(instance, clazz_path)


def subscribe_to_post_save(sender, **kwargs):
    """Callback function called when a model class is ready.
       :func:`carrier_pigeon.select.sender` is registred as a callback of the ``sender``
       model save method if ``sender`` inherits from :class:`~BasicDirtyFieldsMixin`."""
    if BasicDirtyFieldsMixin in sender.mro():
        logger = logging.getLogger('carrier_pigeon.init')
        msg = 'Subscribing post_save for %s model' % sender._meta.object_name
        logger.debug(msg)
        post_save.connect(select, sender=sender)

#
# FIXME move the rest of the code outside of ``__init___.py``
#
# if there is no classes carriere pigeon is not used by the project so we do not
# need to connect post_save
if hasattr(settings, 'CARRIER_PIGEON_CLASSES'):
    for clazz_module in settings.CARRIER_PIGEON_CLASSES:
        register_config(clazz_module)


    class_prepared.connect(subscribe_to_post_save)

