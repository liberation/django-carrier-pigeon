# -*- coding:utf-8 -*-
from time import time
from datetime import datetime

from django.core.management.base import BaseCommand
from django.conf import settings

from carrier_pigeon.models import ItemToPush


class Command(BaseCommand):
    """Remove item :data:`CARRIER_PIGEON_MAX_AGE` old from
    :class:`carrier_pigeon.models.ItemToPush`"""
    help = __doc__

    def handle(self, *args, **options):
        limit = time() - settings.CARRIER_PIGEON_MAX_AGE
        limit = datetime.fromtimestamp(limit)
        rules = ItemToPush.objects.all()
        rules = rules.filter(status=ItemToPush.STATUS.PUSHED,
                             last_push_attempts_date__lte=limit)
        rules.delete()

