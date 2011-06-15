# -*- coding:utf-8 -*-
import os
from time import time

from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    """Cleans up archive content."""
    help = __doc__

    def handle(self, *args, **options):
        path = settings.EXPORT_OUTPUT_DIRECTORY
        for dirpath, dirnames, filenames in os.walk(path):
            for file in filenames:
                file_path = os.path.join(dirpath, file)
                if os.path.isfile(file_path):
                    st_mtime = os.stat(file_path).st_mtime
                    delta = time() - st_mtime
                    if delta  > settings.EXPORT_MAX_AGE:
                        os.remove(file_path)
