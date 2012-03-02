# -*- coding:utf-8 -*-

""" Push items in the ItemToPush queue. """

import os
import logging
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand

from carrier_pigeon import REGISTRY
from carrier_pigeon.models import ItemToPush


logger = logging.getLogger('carrier_pigeon.command.push')


def item_to_push_queue():
    """
    Generator.
    
    Retrieve rows in queue.
    """
    offset = getattr(settings, "CARRIER_SELECT_OFFSET", 10)
    while True:
        qs = ItemToPush.objects.all()
        qs = qs.order_by('creation_date')
        qs = qs.filter(status=ItemToPush.STATUS.NEW)
        rows = qs[:offset]  # don't retrieve too many rows at once
        if len(rows) == 0:
            return
        for row in rows:
            yield row


class Command(BaseCommand):
    """ Push items in the ItemToPush queue. """
    help = __doc__

    def handle(self, *args, **options):

        rules = {}

        for row in item_to_push_queue():
            rule_name = row.rule_name
            try:
                rule = REGISTRY[rule_name]
            except KeyError:
                logger.warning(
                    u'Asked rule "%s" does not exist (instance : %s %d)' % (
                        rule_name, 
                        row.content_object.__class__.__name__, 
                        row.content_object.pk,
                    )
                )
                row.status = ItemToPush.STATUS.PUSH_ERROR
                row.save()
                continue

            logger.debug(u'processing row id=%s, rule_name=%s' %
                                                        (row.pk, row.rule_name))
            # Hook at init
            # (Does this make sense here? Rules instance are persistent...)
            rule.initialize_push()
            # Store the fact that we are working on this item
            # (It will not appear anymore in the queue)
            row.status = ItemToPush.STATUS.IN_PROGRESS
            row.save()
            # Do the job
            rule.process_item(row.content_object, row)
            # Final hook
            rule.finalize_push()
