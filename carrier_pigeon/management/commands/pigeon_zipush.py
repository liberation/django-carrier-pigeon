# -*- coding:utf-8 -*-
""" Archive and push items according to a specific Configuration. """

import logging
from django.core.management.base import BaseCommand
from carrier_pigeon import REGISTRY


logger = logging.getLogger('carrier_pigeon.command.zipush')


def instantiate_class(name):
    components = name.split('.')
    class_name = components[-1]
    del components[-1]
    module_name = '.'.join(components)
    module = __import__(module_name, fromlist=class_name)
    return getattr(module, class_name)()


class Command(BaseCommand):
    """ Archive and push content items as specified. """
    args = '<rule_name rule_name ...>'
    help = __doc__

    def handle(self, *args, **options):
        for rule_name in args:

            # --- Import rule
            try:
                rule = instantiate_class(rule_name)
            except ImportError:
                logger.error(
                    "pigeon_zipush(): Cannot import rule '%s', skipping..." \
                        % rule_name)
                continue
            
            # --- EXPORT ALL THE THINGS!
            rule.initialize_push()
            for item in rule.get_items_to_push():
                rule.export_one(item)
            rule.finalize_push()