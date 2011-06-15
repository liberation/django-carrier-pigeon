import logging

from carrier_pigeon import REGISTRY
from carrier_pigeon.models import ItemToPush
from carrier_pigeon.utils import duplicate_row


logger = logging.getLogger('carrier_pigeon.facility')


def add_item_to_push(instance, rule_name):
    """Adds an item to ``ItemToPush`` table aka. push queue"""
    logger.debug('adding %s for %s config' % (instance, rule_name))
    rule = REGISTRY[rule_name]

    if duplicate_row(rule_name, instance):
        # The item is already in the queue for this url
        logger.debug('This item is already in the queue... skipping.')
    else:
        row = ItemToPush(rule_name=rule_name,
                         content_object=instance)
        row.save()
        logger.debug('Added item in the ItemToPush queue @ %s' % 
                     row.pk)
        rule.post_select(instance)
