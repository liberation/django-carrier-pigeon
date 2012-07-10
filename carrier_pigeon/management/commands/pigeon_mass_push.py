# -*- coding:utf-8 -*-
""" Archive and push items according to a specific Configuration. """

import logging
from django.core.management.base import BaseCommand

from carrier_pigeon.registry import REGISTRY


logger = logging.getLogger('carrier_pigeon.command.mass_push')


class Command(BaseCommand):
    """ Archive and push content items as specified. """
    args = '<rule_name [get_item_to_push_argument get_item_to_push_argument ...]>'
    help = __doc__

    def handle(self, *args, **options):
        rule_name = args[0]
        try:
            rule = REGISTRY[rule_name]
        except KeyError:
            self.stdout.write(u"Sorry, rule '%s' does not exist" % rule_name)
        else:
            # --- EXPORT ALL THE THINGS! \o/
            rule.initialize_push()
            files = []
            for item in rule.get_items_to_push(*args[1:]):
                files += rule.process_item(item)
            rule.finalize_push(files)
            self.stdout.write('Job ran correctly')
