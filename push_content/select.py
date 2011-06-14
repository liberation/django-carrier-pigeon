import logging

from push_content.models import ItemToPush
from push_content import REGISTRY
from push_content.utils import join_url_to_directory


logger = logging.getLogger('push_content.select')


def filter(rule_name, configuration, instance, created):
    """Returns True if the partner configuration validates
    this instance, False otherwise."""
    try:
        validation = configuration.filter_by_instance_type(instance)
    except Exception, e:
        logger.error('error during filter_by_instance_type')
        logger.error('catched exception message: %s' % e.message)
        row = ItemToPush(rule_name=rule_name,
                         content_object=instance)
        row.status = ItemToPush.STATUS.FILTER_BY_INSTANCE_TYPE
        row.message = "%s: %s" % (e.__class__.__name__, e.message)
        row.save()
        return False
    if not validation:
        logger.debug('Item failed instance filter')
        return False

    if not created:

        try:
            validation = configuration.filter_by_updates(instance)
        except Exception, e:
            logger.error('error during filter_by_updates')
            logger.error('catched exception message: %s' % e.message)
            row = ItemToPush(rule_name=rule_name,
                             content_object=instance)
            row.status = ItemToPush.STATUS.FILTER_BY_UPDATES_ERROR
            row.message = "%s: %s" % (e.__class__.__name__, e.message)
            row.save()
            return False

        if not validation:
            logger.debug('Item failed updates filter')
            return False

    try:
        validation = configuration.filter_by_state(instance)
    except Exception, e:
        logger.error('error during filter_by_state')
        logger.error('catched exception message: %s' % e.message)
        row = ItemToPush(rule_name=rule_name,
                         content_object=instance)
        row.status = ItemToPush.STATUS.FILTER_BY_STATE_ERROR
        row.message = "%s: %s" % (e.__class__.__name__, e.message)
        row.save()
        return False

    if not validation:
        logger.debug('Item failed state filter')
        return False
    return True


def select(sender, instance=None, created=False, **kwargs):
    """Add instance to ItemToPush queue for each partner that
    validated the instance."""
    logger.debug('post_save caught for %s?pk=%s' %
                 (instance._meta.object_name, instance.pk))

    for rule_name, configuration in REGISTRY.iteritems():
        logger.debug('selecting Item for `%s` rule_name' % rule_name)
        # if instance doesn't match configuration
        # try another rule_name
        if not filter(rule_name, configuration, instance, created):
            continue

        # try to create a row for each push_url
    logger.debug('end of select')
