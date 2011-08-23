=====================
django-carrier-pigeon
=====================

Kesako ?
========

django-carrier-pigeon helps to send content over the internet based on
rules that are defined in your project. It's used at liberation.fr to
keep partners up-to-date about the content available on the website.

This applications comes with several commands:

- ``pigeon_push`` : pushes items until the end
- ``pigeon_clean_queue`` : cleans the queue from already pushed items. It's
  configured with ``CARRIER_PIGEON_MAX_AGE``
- ``pigeon_clean_export`` : cleans the export file directory from old files.
  It's configured with ``CARRIER_PIGEON_MAX_AGE``
- ``pigeon_check`` is provided to check now and then that ItemToPush objects
  are corectly processed by the ``pigeon_push`` command. Check out the ``pigeon_check.py``
  file inside ``./management/commands/`` for more information about how it works.
  If you plan on using this command you have to setup two additionnal settings:
  ``CARRIER_PIGEON_CHECK_OLD_AGE`` & ``CARRIER_PIGEON_CHECK_TOO_OLD_AGE``.


Dependencies
============

 - ``django-extended-choices``, liberation fork: https://github.com/liberation/django-extended-choices


Supported push methods
======================

- dummy (for testing purpose)
- ftp


Setup
=====

Add ``carrier_pigeon`` to ``INSTALLED_APPS`` in ``settings.py``

configuration
-------------

You have to define this constants in ``settings.py``::

  CARRIER_PIGEON_MAX_AGE = 3600*24*30 # 30 days
  CARRIER_PIGEON_OUTPUT_DIRECTORY = os.path.join(SITE_ROOT, 'tmp', 'export')
  CARRIER_PIGEON_MAX_PUSH_ATTEMPS = 5


Add rules
-------------

First you have to inherit classes you want to be able to push with
``carrier_pigeon.models.BasicDirtyFieldsMixin``. This class will give
the ability to detect changed fields in a save process.

Then you have to configure rules. Configuration is done with python
class. You have to define a class in a file called ``carrier_pigeon_config.py``.
Here is an example configuration class::


  from carrier_pigeon.configuration import DefaultConfiguration


  class ExampleConfig(DefaultConfiguration):
      def filter_by_instance_type(self, instance):
          return (instance._meta.object_name in ['Article'] and
                  instance._meta.app_label in ['libe'])

      def filter_by_updates(self, instance):
          # Check here the fields that may have changed to make an item candidate
          if 'access' in instance._modified_attrs:
              return True
          return False

      def filter_by_state(self, instance):
          # Check here the state of the item to be candidate
          if instance.access = 0:
              return True
          return False

      def get_directory(self, instance):
          return '/test/'


In your ``settings.py`` or ``local_settings.py`` you have to add these contants::

  CARRIER_PIGEON_CLASSES = ('myproject.carrier_pigeon_config.ExampleConfig',)
  CARRIER_PIGEON_PUSH_URLS = {'exampleconfig': ('ftp://my.example.com',)}

See ``DefaultConfiguration`` class for more information on how to setup your
own configuration classes.

If you did not overided other method from ``DefaultConfiguration``, the next step
is to add templates for each export rule and each models you  want to export.
For example a template for a model named ``Article`` from an app named ``libe``
for the export rule ``Test``, the template should be in the template path
``export/test/libe_article.xml``.

cron
----

You have to setup a cron, preferably fcron, to run every x minutes after each
run to execute ``pigeon_push`` command.

You can run ``clean_push_queue`` & ``clean_export_files`` every now and them
to clean up database from fullfilled rules and remove old files from ``CARRIER_PIGEON_OUTPUT_DIRECTORY``.

logging
-------

You can configure to receive emails when the app logs errors to easly keep an
eye on pigeon_push.

How to add a push method
------------------------

You will need to modify ``send`` function in ``pusher.py``

TODO
----

 - make a register for adding custom push methods
