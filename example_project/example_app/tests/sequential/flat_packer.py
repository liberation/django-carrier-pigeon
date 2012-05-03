from example_app.tests.sequential.base import SequentialTests

from django.core.management import call_command


# This is exactly the same as onthefly_zip_packer except 
# pushed content is zipped before sending

class BelovedPartnerTests(SequentialTests):
    """Check proper behavior of BelovedPartner configuration"""

    tested_configuration_name = 'belovedpartner'

    def test_pigeon_push(self):
        call_command('pigeon_push')
        self._test_content()
