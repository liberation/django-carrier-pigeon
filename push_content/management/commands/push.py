# -*- coding:utf-8 -*-
"""Push items in the ItemToPush queue"""
import os
import logging
from datetime import datetime

from django.conf import settings

from django.core.management.base import BaseCommand

from push_content.models import ItemToPush

from push_content.pusher import send

from push_content.utils import URL
from push_content.utils import join_url_to_directory

from push_content import REGISTRY


logger = logging.getLogger('push_content.command.push')


def get_first_row_in_queue():
    """Get the first row in the queue that 
    can be processed"""
    try:
        row = ItemToPush.objects.all()
        row = row.order_by('creation_date')
        row = row.filter(status=ItemToPush.STATUS.NEW)
        row = row[0]
        return row
    except IndexError:
        logger.debug('no more item to push')
        return None


class Command(BaseCommand):
    """Push items in the ItemToPush queue."""
    help = __doc__

    def handle(self, *args, **options):
        row = get_first_row_in_queue()

        if not row:
            return  # there is no more rows to push

        while True:
            logger.debug('processing row id=%s, rule_name=%s' %
                         (row.id, row.rule_name))
            row.status = ItemToPush.STATUS.IN_PROGRESS
            row.save()

            rule_name = row.rule_name
            rule = REGISTRY[rule_name]

            instance = row.content_object

            # build output
            try:
                output = rule.output(instance)
            except Exception, e:
                message = 'Exception ``%s`` raised: %s ' % (
                    e.__class__.__name__, e.message)
                logger.error(message)
                row.status = ItemToPush.STATUS.OUTPUT_GENERATION_ERROR
                row.message = message
                row.save()
                logger.debug('nothing to push')
                # setting up next loop iteration
                row = get_first_row_in_queue()
                if not row:
                    return
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
                    logger.debug('validation ``%s`` failed !')
                    message = 'catched exception %s : %s' % (
                        e.__class__.__name__, e.message)
                    logger.debug(message)
                    row.status = ItemToPush.STATUS.VALIDATION_ERROR
                    if row.message != None:
                        row.message += '\n' + message
                    else:
                        row.message = message
                    row.save()

            if not validation:  # if one validator did not pass we
                                # do no want to send the file
                # setting up next loop iteration
                row = get_first_row_in_queue()
                if not row:
                    return
                continue
            output_filename = rule.get_output_filename(instance)

            # build output file path for archiving
            output_directory = settings.PUSH_CONTENT_OUTPUT_DIRECTORY
            output_directory += '/%s/' % rule_name

            # create output_directory if it doesn't exists
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            output_path = '%s/%s' % (output_directory, output_filename)

            # write output file
            f = open(output_path, 'w')
            f.write(output)
            f.close()

            target_directory = None
            try:
                target_directory = rule.get_directory(instance)
            except Exception, e:
                logger.error('error during ``get_directory``')
                logger.error('catched exception message: %s' % e.message)
                row = ItemToPush(rule_name=rule_name,
                                 content_object=instance)
                row.status = ItemToPush.STATUS.GET_DIRECTORY_ERROR
                row.message = "%s: %s" % (e.__class__.__name__, e.message)
                row.save()
                return None

            for push_url in rule.push_urls:
                target_url = join_url_to_directory(push_url, target_directory)
                logger.debug('target url is ``%s``' % target_url)
                target_url = URL(target_url)

                # try to send
                max_ = settings.PUSH_CONTENT_MAX_PUSH_ATTEMPS
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

            # try to fetch a new row
            row = get_first_row_in_queue()
            if not row:
                return
