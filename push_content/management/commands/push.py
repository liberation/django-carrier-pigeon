# -*- coding:utf-8 -*-
"""Push items in the ItemToPush queue"""
import os
import logging
from datetime import datetime

from django.conf import settings

from django.core.management.base import BaseCommand
from django.template import Context
from django.template import loader
from django.template.base import TemplateDoesNotExist

from push_content.models import ItemToPush
from push_content.pusher import send
from push_content.utils import URL
from push_content import REGISTRY

logger = logging.getLogger('push_content.command.push')


def get_first_row_in_queue():
    try:
        row = ItemToPush.objects.all()
        row = row.order_by('creation_date')
        row = row.filter(status=10)
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
            logger.debug('processing row id=%s, push=%s' %
                         (row.id, row.target_url))
            row.status = ItemToPush.STATUS.IN_PROGRESS
            row.save()
 
            rule_name = row.rule_name
            configuration = REGISTRY[rule_name]

            object = row.content_object

            # build template file path
            app_label = row.content_object._meta.app_label.lower()
            class_name = row.content_object._meta.module_name
            template_name = '%s_%s.xml' % (app_label, class_name)
            
            template_path = 'push_content/%s/%s' % (rule_name, template_name)

            # try to fetch template file
            try:
                template = loader.get_template(template_path)
            except TemplateDoesNotExist:
                message = 'Template %s does not exist' % template_path
                logger.error(message)
                row.status = ItemToPush.STATUS.TEMPLATE_NOT_FOUND
                row.message = message
                row.save()
            else:
                # build template
                context = configuration.get_extra_context(object)
                context['object'] = object
                context = Context(context)
                output = template.render(context)

                output_filename = configuration.get_output_filename(object)
                target_url = URL(row.target_url)

                # build output file path for archiving
                output_directory = settings.PUSH_CONTENT_OUTPUT_DIRECTORY
                output_directory += '/%s/%s' % (rule_name,
                                                target_url.path)

                # create output_directory if it doesn't exists
                if not os.path.exists(output_directory):
                    os.makedirs(output_directory)
                output_path = '%s/%s' % (output_directory, output_filename)

                # write output file
                f = open(output_path, 'w')
                f.write(output)
                f.close()

                # try to send
                max_push_attempt = settings.PUSH_CONTENT_MAX_PUSH_ATTEMPS
                for push_attempt_num in xrange(max_push_attempt):
                    logger.debug('push attempt %s' % push_attempt_num)
                    row.push_attempts += 1
                    row.last_push_attempts_date = datetime.now()
                    row.save()

                    if send(row, target_url, output_path):
                        row.status = ItemToPush.STATUS.PUSHED
                        row.save()
                        logger.debug('succeeded')
                        break # send succeded, exit the for-block
                    else:
                        logger.error('send failed')

            # try to fetch a new row
            row = get_first_row_in_queue()
            if not row:
                return
