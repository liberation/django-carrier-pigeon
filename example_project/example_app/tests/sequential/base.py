import os
import shutil
import hashlib
from StringIO import StringIO
from datetime import date

from django.conf import settings
from django.core.files import File

from carrier_pigeon.models import ItemToPush

from example_app.models import Photo
from example_app.models import Story
from example_app.tests.base import ImplementationBaseTests


# This is exactly the same as onthefly_zip_packer except 
# pushed content is zipped before sending

class SequentialTests(ImplementationBaseTests):
    """Check proper behavior of AnotherBelovedPartner configuration"""

    def setUp(self):
        super(SequentialTests, self).setUp()

        settings.CARRIER_PIGEON_PUSH_URLS = {
            self.tested_configuration_name: (
                "dummy://user:pwd@ftp.belovedpartner.org",
                ),
        }

        # create Photo instance

        # build a random filename
        m = hashlib.sha1()
        m.update(os.urandom(24))
        filepath = '/tmp/%s.jpeg' % m.hexdigest()
        # open and write photo filename with data
        fd = open(filepath, 'w')
        fd.write('coucou')
        fd.close()
        fd = open(filepath)
        # create Photo object
        photo = Photo(
            title='Egg',
            credits='Chicken',
            caption='An egg created by a chicken',
            original_file=File(fd),
        )
        photo.save()

        # don't forget to clean
        os.remove(filepath)

        # build story objects
        self.stories = []

        # the following two stories will be selected
        # by BelovedPartner configuration
        story = Story(
            title='An egg & and a chicken',
            workflow_state=Story.WORKFLOW_STATE.ONLINE,
            content='a'*500,
            photo=photo,
            updating_date=date(2012, 5, 2),
        )
        story.save()
        self.stories.append(story)
        story = Story(
            title='The dear and the fawn ',
            workflow_state=Story.WORKFLOW_STATE.ONLINE,
            content='a'*500,
            photo=photo,
            updating_date=date(2012, 5, 2),
        )
        story.save()
        self.stories.append(story)

        # This story is not selected
        story = Story(
            title='Tazmania devil dog',
            workflow_state=Story.WORKFLOW_STATE.OFFLINE,
            content='a'*500,
            photo=photo,
            updating_date=date(2012, 5, 2),
        )
        story.save()

    def _test_content(self):
        for story in self.stories:
            filename = 'NEWS_example_app_%s.xml' % story.pk
            filepath = os.path.join(
                self.outbox,
                filename,
            )
            with open(filepath) as f:
                with open(self.data(filename)) as d:
                    self.assertEqual(
                        f.read(),
                        d.read(),
                    )

            photopath = os.path.join(
                self.outbox,
                'medias',
                '1.jpg',
            )
            self.assertTrue(os.path.exists(photopath))
            with open(photopath) as f:
                self.assertEqual(f.read(), 'coucou')
