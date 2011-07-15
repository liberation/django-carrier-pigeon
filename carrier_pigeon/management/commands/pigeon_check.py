# -*- coding:utf-8 -*-
"""Push items in the ItemToPush queue"""
import sys
from datetime import datetime
from datetime import timedelta

from django.core.management.base import BaseCommand

from carrier_pigeon.models import ItemToPush


class Command(BaseCommand):
    """Carrier pigeon health check

    it returns exit code 0 if everything is OK.
    it returns exit code *2* if there are new items 30 minutes old or more
    it returns exit code *1* if there are new items 10 minutes old or more but
    less that 30 minutes"""
    help = __doc__

    def handle(self, *args, **options):
        now = datetime.now()

        min30 = timedelta(seconds=60*30) # 30 minutes
        min30_count = ItemToPush.objects.filter(creation_date__lt=now-min30,
                                                status=ItemToPush.STATUS.NEW).count()
        if min30_count > 0:
            sys.exit(2)

        min10 = timedelta(seconds=60*10) # 10 minutes
        min10_count = ItemToPush.objects.filter(creation_date__lt=now-min10,
                                                status=ItemToPush.STATUS.NEW).count()
        if min10_count > 0:
            sys.exit(1)

        sys.exit(0)
