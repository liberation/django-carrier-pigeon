from mock import patch

from django.test import TestCase
from django.contrib.auth.models import User

from senders import FTPSSender
from configuration import DefaultConfiguration
from models import ItemToPush


class TestConfiguration(DefaultConfiguration):
    def get_items_to_push(self):
        # any object will do the trick
        u = User.objects.create(email='test@test.com', password='test')
        item = ItemToPush(push_url='ftps://woot.foobar.com/ftp/', content_object=u)
        return [item,]


class FTPSTestCase(TestCase):

    def test_ftp_class(self):
        with patch.object(FTPSSender, 'deliver', return_value=True) as mock_deliver:
            config = TestConfiguration()
            for item in config.get_items_to_push():
                config.process_item(item.content_object, item)
        mock_deliver.assert_called_once()
