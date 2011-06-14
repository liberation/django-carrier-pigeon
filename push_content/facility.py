import logging

from push_content import REGISTRY
from push_content.models import ItemToPush
from push_content.utils import join_url_to_directory
from push_content.utils import duplicate_row


logger = logging.getLogger('django_push.facility')


def add_item_to_push(instance, configuration_name):
    configuration = REGISTRY[configuration_name]
    rule_name = configuration.__class__.__name__.lower()

    try:
        target_directory = configuration.get_directory(instance)
    except Exception, e:
        logger.error('error during ``get_directory``')
        logger.error('catched exception message: %s' % e.message)
        row = ItemToPush(rule_name=rule_name,
                         content_object=instance)
        row.status = ItemToPush.STATUS.GET_DIRECTORY_ERROR
        row.message = "%s: %s" % (e.__class__.__name__, e.message)
        row.save()
        return None

    logger.debug('target directory is %s' % target_directory)

    for push_url in configuration.push_urls:
        target_url = join_url_to_directory(push_url, target_directory)

        logger.debug('target url is %s' % target_url)

        # we check that there isn't already a row for that item
        # in the queue

        if duplicate_row(rule_name, target_url, instance):
            # The item is already in the queue for this url
            logger.debug('This item is already in the queue... skipping.')
            continue

        row = ItemToPush(rule_name=rule_name,
                          target_url=target_url,
                          content_object=instance)
        row.save()
        logger.debug('Added item in the ItemToPush queue @ %s'
                     % target_url)
        configuration.is_candidate(row)
