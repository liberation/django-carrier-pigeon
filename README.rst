===================
django-push-content
===================

Kesako django-push-content ?
============================

django-push-content helps to send content over the internet based on
rules that are defined in your project. It's used at liberation.fr to
keep our up-to-date about the content available on the website.

This applications comes with three commands:

- push : pushes items until the end
- clean_push_queue : cleans the queue from already pushed items. It's
  configured with PUSH_CONTENT_MAX_AGE
- clean_export_files : cleans the export file directory from old files.
  It's configured with PUSH_CONTENT_MAX_AGE

Dependencies
============

 - django-extended-choices, liberation fork: https://github.com/liberation/django-extended-choices 

Supported push methods
======================

- ftp

Setup
=====

Add push_content to INSTALLED_APPS in settings.py

configuration
-------------

You have to define 3 constants in settings.py of your project::

  PUSH_CONTENT_MAX_AGE = 3600*24*30 # 30 days
  PUSH_CONTENT_OUTPUT_DIRECTORY = os.path.join(SITE_ROOT, 'tmp', 'export') 
  PUSH_CONTENT_MAX_PUSH_ATTEMPS = 5 


Add rules
-------------

First you have to inherit classes you want to be able to push with 
``BasicDirtyFieldsMixin`` that you can find in ``push_content.models``. This class will give the ability to detect changed fields in a save process 

Then you have to configure rules. Configuration is done with python 
class. You have to define a class in a file called ``push_content_config.py`` (for example) that looks like this one:: 

  from push_content import register


  class Test:
      push_urls = ('ftp://k689kl:s14s5t@localhost', )

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

  register(Test)

Nota : you have to make sure that your file is loaded by Django, for example importing it in the ``__init__.py`` file of the project.

The next step is to add templates for each export rule and each models you 
want to export. For example a template for a model named ``Article`` from 
an app named ``libe`` for the export rule ``Test``, the template should be in 
the template path ``export/test/libe_article.xml``.

cron
----

You have to setup a cron, preferably fcron, to run every x minutes after each 
run to execute ``push`` command.

You can setup ``clean_push_queue`` & ``clean_export_files`` every now and them 
to clean up database from fullfilled rules and removed old files from ``PUSH_CONTENT_OUTPUT_DIRECTORY``.

logging
-------

You can configure to receive emails when the app logs errors to easly keep an 
eye on the if the job is done correctly.

How to add a push method
------------------------

You will need to modify ``send`` function in ``pusher.py``

TODO
----

 - make a register for addind custom push methods