Apllication Configuration
=========================

.. py:data:: CARRIER_PIGEON_CLASSES

It should be a list of class path where carrier pigeon will find
task configurations.

.. py:data:: CARRIER_PIGEON_PUSH_URLS

It should be a dictionnary matching configuration name see
:meth:`carrier_pigeon.configuration.DefaultConfiguration.name`

.. py:data:: CARRIER_PIGEON_OUTPUT_DIRECTORY

The output directory should be a path to a directory where to store files pushed
with the default configuration.

.. py:data:: CARRIER_PIGEON_MAX_PUSH_ATTEMPS

Number of attemps to push an object before aborting,
see :class:`carrier_pigeon.management.commands.pigeon_push.Command`.

.. py:data:: CARRIER_PIGEON_CHECK_OLD_AGE = 10*60

Sets the age first step for items in :class:`carrier_pigeon.models.ItemToPush`
queue. Used in :class:`carrier_pigeon.management.commands.pigeon_check.Command`.

.. py:data:: CARRIER_PIGEON_CHECK_TOO_OLD_AGE = 30*60

Sets the max age for items in :class:`carrier_pigeon.models.ItemToPush`
queue. Used in :class:`carrier_pigeon.management.commands.pigeon_check.Command`.

.. py:data:: CARRIER_SELECT_OFFSET = 10

Sets the number of items fetched when processing items from :class:`carrier_pigeon.models.ItemToPush`
in :class:`carrier_pigeon.management.commands.pigeon_check.Command`. It's not the
number of items processed, but the number of object fetched per iteration, see
:func:`carrier_pigeon.management.commands.pigeon_push.item_to_push_queue` for details.

