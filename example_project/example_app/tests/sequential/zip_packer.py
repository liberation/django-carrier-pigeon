import os
import zipfile

from example_app.tests.sequential.base import SequentialTests

from django.core.management import call_command


class AnotherBelovedPartnerTests(SequentialTests):
    """Check proper behavior of BelovedPartner configuration"""

    tested_configuration_name = 'anotherbelovedpartner'

    def test_pigeon_push(self):
        call_command('pigeon_push')
        listdir = os.listdir(self.outbox)
        self.assertEqual(len(listdir), 2)
        for filename in listdir:
            # unzip file
            path = os.path.join(
                self.outbox,
                filename,
            )
            zzz = zipfile.ZipFile(path)
            zzz.extractall(self.outbox)
        self._test_content()
