from django.test import TestCase

from django.db import models
from django.db.models.signals import class_prepared
from django.db.models.signals import post_save

from carrier_pigeon import REGISTRY, add_instance, subscribe_to_post_save
from carrier_pigeon.configuration import DefaultConfiguration
from carrier_pigeon.models import BasicDirtyFieldsMixin, ItemToPush
from carrier_pigeon.select import select

class Test(DefaultConfiguration):
    push_urls = ('ftp://foo.bar.baz',)

    def filter_by_instance_type(self, instance):
        return True

    def filter_by_updates(self, instance):
        return True

    def filter_by_state(self, instance):
        return True

    def get_directory(self, instance):
        return ''


add_instance(Test())


class Dummy(models.Model, BasicDirtyFieldsMixin):
    foo = models.IntegerField()


post_save.connect(select, sender=Dummy)


class AddToQueueTest(TestCase):
    def test_add_to_queue(self):
        dummy = Dummy(foo=1)
        dummy.save()
        
        qs = ItemToPush.objects.all()
        count = qs.count()
        
        self.assertEqual(count, 1)
        item = qs[0]
        self.assertEqual(item.status, ItemToPush.STATUS.NEW)    
