Getting Started
===============

Project Configuration
---------------------

First thing first, install Django Carrier Pigeon using you favorite tool and add
the application in django settings ``INSTALLED_APPS``.

Configuring your first task
---------------------------

The primary purpose of carrier pigeon is to watch for model saves and send
asynchronously files over ftp. We will illustrate it with an example project
``Messager``.

The ``Messager`` is a short message web application that let you write messages
and push them to a remote location for backup. For this purpose, we will use the
default configuration with the ftp backend.

First thing to do is inherit the Message class from
:class:`carrier_pigeon.BasicDirtyFieldsMixin` in a ``wall`` django app:


.. code-block:: python
    :linenos:

    from django.db import models
    from carrier_pigeon.models import BasicDirtyFieldsMixin


    class Message(models.Model, BasicDirtyFieldsMixin):
        title = models.CharField(max_length=255)
        content = models.TextField()
        share = models.BooleanField(default=False)

Create a new file ``carrier_pigeon_configuration.py`` somewhere in your django
project, and paste the code below, explanation of each method is inlined:

.. code-block:: python
    :linenos:

    from carrier_pigeon.configuration import DefaultConfiguration


    class MessagePushConfiguration(DefaultConfiguration):

        def filter_by_instance_type(self, instance):
            # this configuration is for Message objects
            return instance._meta.object_name in ['Message']

        def filter_by_updates(self, instance):
            # if the object was modified we might like to push it again only if
            # the modification is significant in some way, in this case
            # if the ``share`` attribute was modified
            # this filter is run only if it's an update operation
            if 'share' in instance._modified_attrs:  # _modified_attrs is an attribute
                                                     # provided by BasicDirtyFieldsMixin
              return True
            return False

        def filter_by_state(self, instance):
            # more filter
            if instance.share == True:
              return True
            return False

        def get_directory(self, instance):
            # this is used to provide extra information for the push method
            # in the case of the ftp backend this is the directory we have to push
            # the file to
            return '/test/'

In your ``settings.py`` or ``local_settings.py`` you have to add theses constants:

.. code-block:: python
    :linenos:

    import os

    SITE_ROOT = os.path.dirname(__file__)

    CARRIER_PIGEON_CLASSES = ('my_project_name.path.to.configuration.file.MessagePushConfiguration',)
    CARRIER_PIGEON_PUSH_URLS = {'messagepushconfiguration': ('ftp://user:password@localhost',)}
    CARRIER_PIGEON_OUTPUT_DIRECTORY = os.path.join(SITE_ROOT, 'tmp', 'export')
    CARRIER_PIGEON_MAX_PUSH_ATTEMPS = 5

You have to create the directory structure ``tmp/export/`` at  the root of your
project directory. In order to make this example work you need to have an ftp
server running on your machine on port 21 with an account for an user with
``user`` as username & ``password`` as password and file and directy creation
rights.

The file we will send will be generated from a template the default location is
``carrier_pigeon/%(rule_name_in_lower_case)s/%(app_label)s_%(class_name)s.xml``,
paste below template into the created file:

.. code-block:: xml
    :linenos:

    <message>
      <title>
        {{ object.title }}
      </title>
      <content>
        {{ object.content }}
      </content>
    </message>

To test the configuration you have to use ``pigeon_push`` command::

  $ python manage.py pigeon_push

You can also check if the file was properly generated in
``./tmp/export/messagepushconfiguration/test/wall_message.xml``.

Congratulations you got the basics of carrier pigeon, you can now investigate
the documentation, you might start by settings and commands.

