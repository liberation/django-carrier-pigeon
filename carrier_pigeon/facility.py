import logging

from carrier_pigeon.models import ItemToPush
from carrier_pigeon.utils import duplicate_row


logger = logging.getLogger('carrier_pigeon.facility')


def add_item_to_push(instance, rule_name):
    """Adds an item to ``ItemToPush`` table aka. push queue"""
    logger.debug('adding %s for %s config' % (instance, rule_name))

    from carrier_pigeon import REGISTRY

    try:
        rule = REGISTRY[rule_name]
    except KeyError:
        logger.warning(u'Asked rule "%s" does not exist (instance : %s %d)'
                        % (rule_name, instance.__class__.__name__, instance.pk))
        return

    if duplicate_row(rule_name, instance):
        # The item is already in the queue for this url
        logger.debug('This item is already in the queue... skipping.')
    else:
        for push_url in rule.push_urls:
            row = ItemToPush(rule_name=rule_name,
                             content_object=instance,
                             push_url=push_url)
            row.save()
            logger.debug('Added item in the ItemToPush queue @ %s' %
                         row.pk)
        try:
            model_supervisor = rule.get_supervisor_for_item(instance)
        except:
            pass
        else:
            model_supervisor.post_select(instance)
