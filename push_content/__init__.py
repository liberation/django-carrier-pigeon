import logging

from django.db import models as django_models
from django.db.models.signals import post_save


REGISTRY = {}


from push_content.select import select

from push_content.models import BasicDirtyFieldsMixin


def register(clazz):
    logger = logging.getLogger('push_content.registry')
    name = clazz.__name__.lower()
    logger.debug('Registring %s partner configuration.' % name)
    REGISTRY[name] = clazz()


def load_models():
    """returns models from installed apps that inherits
    BasicDirtyFieldsMixin"""
    logger = logging.getLogger('push_content.init')
    logger.info('Start of configuration')
    logger.debug('Seeking models that inherits BasicDirtyFieldsMixin.')
    # compute classes that we want to catch
    all_class = []

    for app in django_models.get_apps():
        klasses = django_models.get_models(app)
        all_class.extend(klasses)

    selected_models = [klass for klass in all_class
                       if BasicDirtyFieldsMixin in klass.mro()]

    return selected_models

SELECTED_MODELS = load_models()

for model in SELECTED_MODELS:
    logger = logging.getLogger('push_content.init')
    msg = 'Subscribing post_save for %s model' % model._meta.object_name
    logger.debug(msg)
    post_save.connect(select, sender=model)
