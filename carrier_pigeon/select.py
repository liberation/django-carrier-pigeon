import logging

from carrier_pigeon.models import ItemToPush
from carrier_pigeon.facility import add_item_to_push


logger = logging.getLogger('carrier_pigeon.select')


def filter(rule_name, model_supervisor, instance, created):
    """Returns True if the rule model_supervisor validates
    this instance, False otherwise."""

    try:
        validation = model_supervisor.filter_by_instance_type()
    except Exception, e:
        logger.error('error during filter_by_instance_type')
        logger.error('catched exception message: %s' % e.message)
        row = ItemToPush(rule_name=rule_name,
                         content_object=instance)
        row.status = ItemToPush.STATUS.FILTER_BY_INSTANCE_TYPE_ERROR
        row.message = "%s: %s" % (e.__class__.__name__, e.message)
        row.save()
        return False
    if not validation:
        logger.debug('Item failed instance filter')
        return False

    if not created:

        try:
            validation = model_supervisor.filter_by_updates()
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
        validation = model_supervisor.filter_by_state()
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

    from carrier_pigeon import REGISTRY

    for rule_name, configuration in REGISTRY.iteritems():
        logger.debug('selecting Item for `%s` rule' % rule_name)
        # if instance doesn't match configuration
        # try another rule_name
        model_supervisor = None
        try:
            model_supervisor = configuration.get_supervisor_for_item(instance)
        except Exception:
            pass
        if (not model_supervisor
            or not filter(rule_name, model_supervisor, instance, created)):
            continue

        # try to create a row for each push_url
        add_item_to_push(instance, rule_name)
    logger.debug('end of select')
