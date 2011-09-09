# -*- coding:utf-8 -*-
from time import time
from datetime import datetime
from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings

from carrier_pigeon.models import ItemToPush


class Command(BaseCommand):
    """Remove old queue item"""
    help = __doc__

    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dryrun',
            default=False,
            help='Report what will be deleted without actually doing it'),
        )

    def handle(self, *args, **options):
        dryrun = options['dryrun']
        limit = time() - settings.CARRIER_PIGEON_MAX_AGE
        limit = datetime.fromtimestamp(limit)
        rules = ItemToPush.objects.all()
        rules = rules.filter(status=ItemToPush.STATUS.PUSHED,
                             last_push_attempts_date__lte=limit)
        if dryrun:
            output = ''
            for item in rules:
                output += '%s@%s %s\n' % (item.rule_name, item.push_url, item.content_object)
            count = rules.count()
            output += 'Total count of item to be deleted %s' % count
        else:
            rules.delete()

