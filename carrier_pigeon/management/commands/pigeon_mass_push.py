# -*- coding:utf-8 -*-
""" Archive and push items according to a specific Configuration. """

import logging
from django.core.management.base import BaseCommand

from carrier_pigeon import REGISTRY


logger = logging.getLogger('carrier_pigeon.command.mass_push')


class Command(BaseCommand):
    """ Archive and push content items as specified. """
    args = '<rule_name rule_name ...>'
    help = __doc__

    def handle(self, *args, **options):
        for rule_name in args:
            try:
                rule = REGISTRY[rule_name]
            except KeyError:
                logger.warning(u"Sorry, rule '%s' does not exist" % rule_name)
                continue
            
            # --- EXPORT ALL THE THINGS! \o/
            rule.initialize_push()
            for item in rule.get_items_to_push():
                rule.export_item(item)
            rule.finalize_push()