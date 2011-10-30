# -*- coding:utf-8 -*-

import os
import shutil
import logging
import datetime
import threading

from zipfile import ZipFile

from pyftpdlib import ftpserver

from django.db import models
from django.db.models.signals import class_prepared
from django.db.models.signals import post_save
from django.core import management
from django.core.files import File
from django.test import TestCase

from django.contrib.webdesign import lorem_ipsum as lipsum

from libe.constants import WORKFLOW_STATE
from libe.models import Article, Photo, ContentToPhoto
from libe.tests import Factory

from carrier_pigeon import REGISTRY, add_instance, subscribe_to_post_save
from carrier_pigeon.models import BasicDirtyFieldsMixin, ItemToPush
from carrier_pigeon.select import select
from carrier_pigeon.senders import FTPSender
from carrier_pigeon.utils import URL, TreeHash
from carrier_pigeon.configuration import SequentialPusherConfiguration, \
    ZIPPusherConfiguration


TEST_FTP_PORT = 2121
TEST_FTP_LOGIN ='pigeon'
TEST_FTP_PASSWORD = 'rooroo'
TEST_FTP_TARGET_URL = 'ftp://%s:%s@127.0.0.1:%s/' % (
    TEST_FTP_LOGIN, TEST_FTP_PASSWORD, TEST_FTP_PORT
)

TEST_FTP_DIR_REMOTE = os.path.join(os.path.dirname(__file__), 'remote')


TODAY = datetime.datetime.now()
ONE_WEEK_AGO = TODAY - datetime.timedelta(days=7)
TEN_DAYS_AGO = TODAY - datetime.timedelta(days=10)
TWO_WEEKS_AGO = TODAY - datetime.timedelta(days=14)


# --- Helper: FTP server (based on pyftpdlib)

class TestFTPServer:
    def __init__(self):

        homedir = TEST_FTP_DIR_REMOTE
        if not os.path.exists(homedir):
            os.mkdir(homedir, 0775)

        address = ('', TEST_FTP_PORT)

        authorizer = ftpserver.DummyAuthorizer()
        authorizer.add_user(
            TEST_FTP_LOGIN,
            password=TEST_FTP_PASSWORD,
            homedir=homedir,
            perm='elradfmw',
        )

        handler = ftpserver.FTPHandler
        handler.authorizer = authorizer

        self._server = ftpserver.FTPServer(address, handler)

    def serve(self):
        self._server.serve_forever()


class TestFTPServerThread(threading.Thread):
    def __init__(self):
        super(TestFTPServerThread, self).__init__()
        self._server = TestFTPServer()

    def run(self):
        self._server.serve()


ftp = TestFTPServerThread()
ftp.setDaemon(True)
ftp.start()

# --- Helpers

def create_test_photo(filename):
    title = 'Photo: %s' % filename

    F = Factory()
    F.make('Photo', title=title)

    photo = Photo.objects.get(title=title)
    test_picture_filename = "%s/%s" % (
        os.path.realpath(os.path.dirname(__file__)), filename )
    photo.original_file.save(filename, File(open(test_picture_filename), 'rb'))

    return photo

def create_test_article(**kwargs):

    publication_date = kwargs.get('publication_date', datetime.datetime.now())
    workflow_state = kwargs.get('workflow_state', WORKFLOW_STATE.ONLINE)

    F = Factory()

    article = F.make(
        'Article',
        title=lipsum.words(3, common=False),
        content=lipsum.paragraphs(3, common=False),
        publication_date=publication_date,
        workflow_state=workflow_state,
    )

    photos = kwargs.get('photos', list())
    for photo in photos:
        ContentToPhoto.objects.create(content_model=article, photo=photo)

    return article

# --- Utils tests

class TreeHashTest(TestCase):

    def test_01_tree_hash_list_files(self):
        """ Test that a TreeHash properly lists all relevant files. """

        fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        th = TreeHash(fixtures_dir)
        th.hash()
        
        self.assertEqual(
            th._files,
            [
                ('./totoro1.jpg',        42504, 'ae066e37728659c112d38e99d8ff1e65298d51e3'),
                ('./totoro2.jpg',       118176, 'a723bf58b0a847fc597b36d2ee99ec9c2b2f8051'),
                ('./totoro3.jpg',        34676, '9eb0f26dda4bb2453cb2e47521a401ad011f3f42'),
                ('./katee/sackhoff.jpg', 58678, '052fe0d9f4854d1a50f2d5abd1d9a97202af755e'),
            ]
        )

    def test_02_tree_hash_hash(self):
        """ Test that a TreeHash properly computes its hash. """

        fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
        th = TreeHash(fixtures_dir)
        th.hash()

        self.assertEqual(
            th._hash,
            '6ce8df3f20be3079273f3a420a1ddbb613e40980'
        )


# --- Sequential pusher tests

"""

class TestSequentialConfiguration(SequentialPusherConfiguration):
    push_urls = ('ftp://foo.bar.baz',)

    def filter_by_instance_type(self, instance):
        return True

    def filter_by_updates(self, instance):
        return True

    def filter_by_state(self, instance):
        return True

    def get_directory(self, instance):
        return 'foo/bar/baz'
add_instance(TestSequentialConfiguration())

class TestFilterByInstanceTypeFalse(TestSequentialConfiguration):
    def filter_by_instance_type(self, instance):
        return False
add_instance(TestFilterByInstanceTypeFalse())

class TestFilterByUpdatesFalse(TestSequentialConfiguration):
    def filter_by_updates(self, instance):
        return False
add_instance(TestFilterByUpdatesFalse())

class TestFilterByStateFalse(TestSequentialConfiguration):
    def filter_by_state(self, instance):
        return False
add_instance(TestFilterByStateFalse())

class Dummy(models.Model, BasicDirtyFieldsMixin):
    foo = models.IntegerField()
post_save.connect(select, sender=Dummy)


class ManagerTest(TestCase):
    def test_new_filter(self):
        dummy = Dummy(foo=1)
        dummy.save()

        qs = ItemToPush.objects.new()
        count = qs.count()

        self.assertEqual(count, 2)

    def test_new_filter_chainable(self):
        dummy = Dummy(foo=1)
        dummy.save()

        qs = ItemToPush.objects.new().new()
        count = qs.count()

        self.assertEqual(count, 2)

    #FIXME: add tests for other choices

"""

class AddToQueueTest(TestCase):
    def test_add_to_queue(self):
        """This actually also tests that the filtering is corretly done
        through the presence of enough carrier pigeon configuration classes
        in the registry. see :class:Test, :class:TestFilterByInstanceTypeFalse,
        :class:TestFilterByUpdatesFalse, :class:TestFilterByStateFalse"""
        dummy = Dummy(foo=1)
        dummy.save()

        qs = ItemToPush.objects.filter(status=ItemToPush.STATUS.NEW)
        count = qs.count()

        self.assertEqual(count, 2)
        for item in qs:
            self.assertEqual(item.status, ItemToPush.STATUS.NEW)

    def test_add_to_queue_update(self):
        """Test whether filter by updates is correctly handled"""
        dummy = Dummy(foo=1)
        dummy.save()

        qs = ItemToPush.objects.filter(status=ItemToPush.STATUS.NEW)
        count = qs.count()

        self.assertEqual(count, 2)
        for item in qs:
            self.assertEqual(item.status, ItemToPush.STATUS.NEW)

        ItemToPush.objects.all().delete()

        dummy = Dummy.objects.get(pk=dummy.pk)
        dummy.foo = 2
        dummy.save()

        qs = ItemToPush.objects.new()
        count = qs.count()

        self.assertEqual(count, 1)
        for item in qs:
            self.assertEqual(item.status, ItemToPush.STATUS.NEW)


# --- Mass-pusher tests

class TestMassPusher(ZIPPusherConfiguration, FTPSender):
    TARGET_URL = TEST_FTP_TARGET_URL
    EXPORT_BINARIES_RELATIONSHIP_DEPTH = 2

    def get_items_to_push(self):
        """
        For this test configuration, the rule is fairly simple:
        All online articles which have been published in the past 10 days.
        """
        return Article.objects.filter(
            workflow_state=WORKFLOW_STATE.ONLINE,
            publication_date__gte=TEN_DAYS_AGO
        )

    def get_template_name(self, instance):
        return 'test_article.xml'

    def get_template_path(self, instance, template_name):
        return template_name

    def item_binaries(self, item, depth):
        binaries = list()
        for photo in item.get_photos():
            binaries.append(photo.original_file.path)
        return binaries            


class TestMassPusherNoBinaries(TestMassPusher):
    EXPORT_BINARIES = False
    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = False


class TestMassPusherLocalBinaries(TestMassPusher):
    EXPORT_BINARIES = True
    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = False


class TestMassPusherLinkedBinaries(TestMassPusher):
    EXPORT_BINARIES = True
    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = True
 

class MassPusherTest(TestCase):
    def setUp(self):    

        photo1 = create_test_photo('fixtures/totoro1.jpg')
        photo2 = create_test_photo('fixtures/totoro2.jpg')
        photo3 = create_test_photo('fixtures/totoro3.jpg')
        photo4 = create_test_photo('fixtures/katee/sackhoff.jpg')

        article1 = create_test_article(
            publication_date=TODAY,
            workflow_state=WORKFLOW_STATE.ONLINE,
            photos=[photo4]
        )
        article2 = create_test_article(     # --- OFFLINE!
            publication_date=TODAY,
            workflow_state=WORKFLOW_STATE.OFFLINE,
        )
        article3 = create_test_article(
            publication_date=ONE_WEEK_AGO,
            workflow_state=WORKFLOW_STATE.ONLINE,
        )
        article4 = create_test_article(
            publication_date=ONE_WEEK_AGO,
            workflow_state=WORKFLOW_STATE.ONLINE,
            photos=[photo1, photo3]
        )
        article5 = create_test_article(
            publication_date=ONE_WEEK_AGO,
            workflow_state=WORKFLOW_STATE.ONLINE,
            photos=[photo2, photo4]
        )
        article6 = create_test_article(     # --- TOO OLD!
            publication_date=TWO_WEEKS_AGO,
            workflow_state=WORKFLOW_STATE.ONLINE,
            photos=[photo1, photo2, photo3, photo4]
        )

    def runTest(self, config):
        config.initialize_push()
        items = config.get_items_to_push()
        self.assertEqual(len(items), 4)

        for item in items:
            logging.debug("runTest(): item: %s" % str(item))
            config.export_item(item)
        config.finalize_push()

        validation_path = os.path.join(TEST_FTP_DIR_REMOTE, 'validation')
        try:
            shutil.rmtree(validation_path)
        except OSError:
            pass

        archive_fn = os.path.join(TEST_FTP_DIR_REMOTE, config._archive_name)
        archive = ZipFile(archive_fn, 'r')
        archive.extractall(validation_path)

        remote_checksum = TreeHash(validation_path).hash()

        logging.debug("runTest(): archive_filename: %s" % archive_fn)
        logging.debug("runTest():  validation_path: %s" % validation_path)
        logging.debug("runTest():   local_checksum: %s" % config._local_checksum)
        logging.debug("runTest():  remote_checksum: %s" % remote_checksum)

        if config._local_checksum == remote_checksum:
            logging.info("")
            logging.info("**********************************")
            logging.info("***  H U G E  S U C C E S S !  ***")
            logging.info("**********************************")
            logging.info("")

        self.assertEqual(config._local_checksum, remote_checksum)

    def tearDown(self):
        validation_path = os.path.join(TEST_FTP_DIR_REMOTE, 'validation')
        try:
            shutil.rmtree(validation_path)
        except OSError:
            pass

    def test_01_no_binaries(self):
        """ Test proper delivery without binaries. """
        self.runTest(TestMassPusherNoBinaries())

    def test_02_local_binaries(self):
        """ Test proper delivery with local binaries only. """
        self.runTest(TestMassPusherLocalBinaries())

    def test_03_linked_binaries(self):
        """ Test proper delivery with local and linked binaries. """
        self.runTest(TestMassPusherLinkedBinaries())

