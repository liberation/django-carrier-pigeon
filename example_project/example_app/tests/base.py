import os
import shutil

from django.conf import settings
from django.test import TestCase

from carrier_pigeon.registry import REGISTRY


REGISTRY_COPY = dict(REGISTRY)

class ImplementationBaseTests(TestCase):

    @property
    def outbox(self):
        path = os.path.join(
            settings.SITE_ROOT,
            'tmp',
            'export',
            self.tested_configuration_name,
            'outbox',
        )
        return path

    def clean_outbox(self):
        path = self.outbox
        if os.path.exists(path):
            shutil.rmtree(path)

    def data(self, filename):
        path = os.path.join(
            os.path.dirname(__file__),
            'data',
            self.tested_configuration_name,
            filename
        )
        return path

    def setUp(self):
        # remove from registred configuration
        # configuration that we do no test in current test class
        REGISTRY.clear()
        for key, item in REGISTRY_COPY.iteritems():
            print key, item
            if key == self.tested_configuration_name:
                REGISTRY[key] = item
        self.clean_outbox()

    def tearDown(self):
        self.clean_outbox()

        # clean media content
        path = os.path.join(
            settings.SITE_ROOT,
            'medias',
            'photo',
        )
        shutil.rmtree(path)
