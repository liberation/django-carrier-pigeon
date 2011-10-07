# -*- coding:utf-8 -*-
import os
from time import time
from optparse import make_option

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    """Cleans up archive content."""
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
        if dryrun:
            output = ''
            count = 0
        path = settings.CARRIER_PIGEON_OUTPUT_DIRECTORY
        for dirpath, dirnames, filenames in os.walk(path):
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                if os.path.isfile(file_path):
                    st_mtime = os.stat(file_path).st_mtime
                    delta = time() - st_mtime
                    if delta  > settings.CARRIER_PIGEON_MAX_AGE:
                        if dryrun:
                            output += "%s\n" % file_path
                            count += 1
                        else:
                            os.remove(file_path)
        if dryrun:
            print output
            print 'Total count of file to be deleted %s' % count

