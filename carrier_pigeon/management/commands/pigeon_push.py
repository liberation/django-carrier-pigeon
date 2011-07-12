# -*- coding:utf-8 -*-
"""Push items in the ItemToPush queue"""
import os
import logging
from datetime import datetime

from django.conf import settings

from django.core.management.base import BaseCommand

from carrier_pigeon.models import ItemToPush
from carrier_pigeon.pusher import send
from carrier_pigeon.utils import URL
from carrier_pigeon.utils import join_url_to_directory
from carrier_pigeon import REGISTRY


logger = logging.getLogger('carrier_pigeon.command.push')


def item_to_push_queue():
    """
    Generator.
    
    Retrieve rows in queue.
    """
    limit = getattr(settings, "CARRIER_SELECT_LIMIT", 10)
    while True:
        qs = ItemToPush.objects.all()
        qs = qs.order_by('creation_date')
        qs = qs.filter(status=ItemToPush.STATUS.NEW)
        rows = qs[:limit]
        if len(rows) == 0:
            return
        for row in rows:
            yield row


class Command(BaseCommand):
    """Push items in the ItemToPush queue."""
    help = __doc__

    def handle(self, *args, **options):
        for row in item_to_push_queue():
            logger.debug(u'processing row id=%s, rule_name=%s' %
                                                        (row.pk, row.rule_name))
            row.status = ItemToPush.STATUS.IN_PROGRESS
            row.save()

            rule_name = row.rule_name
            rule = REGISTRY[rule_name]

            instance = row.content_object

            # build output
            try:
                output = rule.output(instance)
            except Exception, e:
                message = u"Exception during output generation. "
                message += u'Exception ``%s`` raised: %s ' % (
                                e.__class__.__name__, e.message)
                row.status = ItemToPush.STATUS.OUTPUT_GENERATION_ERROR
                row.message = message
                row.save()
                logger.error(message, exc_info=True)
                continue

            # validate output
            validation = True
            for validator in rule.validators:
                try:
                    validator(output)
                    logger.debug('validation ``%s`` passed successfully'
                                                           % validator.__name__)
                except Exception, e:
                    validation = False
                    message = u"Validation ``%s`` failed ! " % validator.__name__
                    message += u'Catched exception %s : %s' % (
                                e.__class__.__name__, e.message)
                    row.status = ItemToPush.STATUS.VALIDATION_ERROR
                    if row.message != None:
                        row.message += '\n' + message
                    else:
                        row.message = message
                    logger.error(message, exc_info=True)
                    row.save()

            if not validation:  # if one validator did not pass we
                                # do no want to send the file
                logger.debug('the output was not validated')
                continue
            
            output_filename = rule.get_output_filename(instance)
            
            # Get remote target directory (used also in archiving)
            target_directory = None
            try:
                target_directory = rule.get_directory(instance)
            except Exception, e:
                message = u"Error during ``get_directory``. "
                message += u"%s: %s" % (
                                e.__class__.__name__, e.message)
                row = ItemToPush(rule_name=rule_name,
                                 content_object=instance)
                row.status = ItemToPush.STATUS.GET_DIRECTORY_ERROR
                row.message = message
                row.save()
                logger.error(message, exc_info=True)
                continue

            # build output file path for archiving
            output_directory = settings.CARRIER_PIGEON_OUTPUT_DIRECTORY
            output_directory += '/%s/' % rule_name
            output_directory += '/%s/' % target_directory

            # create output_directory if it doesn't exists
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            output_path = '%s/%s' % (output_directory, output_filename)

            # write output file
            f = open(output_path, 'w')
            f.write(output)
            f.close()
            
            # End of archiving
            
            # Prepare sending
            target_url = join_url_to_directory(row.push_url,
                                               target_directory)
            logger.debug('target url is ``%s``' % target_url)
            target_url = URL(target_url)

            # try to send
            max_ = settings.CARRIER_PIGEON_MAX_PUSH_ATTEMPS
            for push_attempt_num in xrange(max_):
                logger.debug('push attempt %s' % push_attempt_num)
                row.push_attempts += 1
                row.last_push_attempts_date = datetime.now()
                row.save()

                if send(row, target_url, output_path):
                    row.status = ItemToPush.STATUS.PUSHED
                    row.save()
                    logger.debug('succeeded')
                    break  # send succeded, exit the for-block
                else:
                    logger.error('send failed')
