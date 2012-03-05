# -*- coding:utf-8 -*-

import os
import os.path
import shutil
import logging

from django.conf import settings

from carrier_pigeon.models import ItemToPush
from carrier_pigeon.senders import SENDER_MAPPING
from carrier_pigeon.utils import URL, TreeHash, zipdir


logger = logging.getLogger('carrier_pigeon.configuration')


class DefaultConfiguration(object):
    """
    Abstract class for all configuration types.
    
    You must inherit from it to create a new type, but not when using carrier pigeon.
    For this, you have to inherit one of the two types already existing:
    - SequentialPusherConfiguration
    - ZIPPusherConfiguration
    """

    @property
    def name(self):
        return self.__class__.__name__.lower()

    @property
    def push_urls(self):
        """ Remote locations urls where to push content. """
        try:
            return settings.CARRIER_PIGEON_PUSH_URLS[self.name]
        except (AttributeError, KeyError):
            logger.warning(u'No push url setted for rule "%s"' % self.name)
            return []

    def initialize_push(self):
        """ Right here, it's nothing more than a placeholder, but you may use
        this method in your subclass if you need a hook to execute some code
        before looping on the items to export. """

        pass

    def get_supervisor_for_item(self, item):
        """
        Return the correct supervisor for the item.

        You *must* implement this method.
        """
        raise NotImplementedError("You must implement this method.")

    def prevent_from_failing(self, func, error_status, row, func_args=None,
                                                func_kwargs=None, default=None):
        """
        Wrapper that call some function, catch any error raised and store it.
        """
        if func_args is None:
            func_args = list()
        if func_kwargs is None:
            func_kwargs = dict()
        returned = default

        try:
            returned = func(*func_args, **func_kwargs)
        except Exception, e:
            message = (u"""Exception during %s call. """
                       u"""Exception ``%s`` raised: %s""") % (
                           func.__name__,
                           e.__class__.__name__,
                           e.message,
                       )
            if row:
                row.status = error_status
                row.message = message
                row.save()
            logger.error(message, exc_info=True)
        return returned

    @property
    def root_directory(self):
        """
        Returns the root directory of the configuration.

        All other pathes are relative to this directory.
        """
        return os.path.join(
            settings.CARRIER_PIGEON_OUTPUT_DIRECTORY,
            self.name,
        )

    @property
    def working_directory(self):
        """
        Effective directory where the file are stored by the OutputMakers.
        """
        return os.path.join(
            self.root_directory,
            self.tmp_directory,
        )

    @property
    def tmp_directory(self):
        """
        Relative working directory. Used by archive pushers to store temporary
        the files that will be archived.
        """
        return ""

    def output_files_from_item(self, item, row=None):
        """
        Export one item. Main entry point of this class's methods.

        `item` is a content to push
        `row` is the optionnal correspondant ItemToPush instance
        (only for sequential mode).
        """

        output_files = []

        # --- Retrieve model supervisor
        supervisor = self.prevent_from_failing(
            self.get_supervisor_for_item,
            ItemToPush.STATUS.SUPERVISOR_ERROR,
            row,
            func_args=[item],
        )

        if not supervisor:
            return output_files

        # --- Retrieve ouput makers
        output_makers = self.prevent_from_failing(
            supervisor.get_output_makers,
            ItemToPush.STATUS.OUTPUT_MARKER_ERROR,
            row,
            default=[],
        )

        # --- Build outputs
        for output_maker in output_makers:
            output = self.prevent_from_failing(
                output_maker.output,
                ItemToPush.STATUS.OUTPUT_GENERATION_ERROR,
                row,
            )
            if not output:
                continue

            # --- Validate output
            validators = output_maker.validators
            # If there are validators, set the validation to False
            # because validors return True if validation passed and raise
            # an error if not
            if validators:
                validation = False
                for validator_class in validators:
                    validator = validator_class(output, output_maker)
                    validation = self.prevent_from_failing(
                        validator.validate,
                        ItemToPush.STATUS.VALIDATION_ERROR,
                        row,
                        default=False
                    )
                    if not validation:
                        break  # escape from first for loop

                if not validation:  # --- If one validator did not pass we
                                    #      do no want to send the file
                    logger.debug('the output was not validated')
                    continue  # We don't want the export process to be stopped
                              # Jump to next output

            # --- Create output directory if necessary
            if not os.path.exists(output_maker.local_final_directory):
                os.makedirs(output_maker.local_final_directory)

            # --- Release the final file locally
            local_final_path = self.prevent_from_failing(
                output_maker.release,
                ItemToPush.STATUS.OUTPUT_GENERATION_ERROR,
                row,
                func_args=[output],
            )

            if local_final_path:
                output_files.append(local_final_path)

        # --- Manage related items, if any
        for related_item in supervisor.get_related_items():
            related_files = self.output_files_from_item(related_item, row)
            output_files += related_files

        return output_files

    def process_item(self, item, row=None):
        return self.output_files_from_item(item, row)

    def finalize_push(self):
        """ Right here, it's nothing more than a placeholder, but you may use
        this method in your subclass if you need a hook to execute some code
        after looping on the items to export. For example, if the exported
        files need to be archived and sent, this will happen here. """

        pass

    def deliver(self, files, target_url, row=None):
        """Defines from url scheme the right sender to use, and calls it."""
        try:
            sender_class = SENDER_MAPPING[target_url.scheme]
        except KeyError:
            logger.error('url scheme %s not supported' % target_url.scheme)
        else:
            sender = sender_class(self)
            return sender.deliver(files, target_url, row)


class SequentialPusherConfiguration(DefaultConfiguration):
    """
    Configurations inheriting this class will send their files onto the
    destination server one by one, progressively.

    Associated management command: python manage.py pigeon_push
    """

    def process_item(self, item, row):

        files = self.output_files_from_item(item, row)

        target_url = row.push_url
        logger.debug('export_item(): target url: ``%s``' % target_url)
        target_url = URL(target_url)

        return self.deliver(files, target_url, row)


class MassPusherConfiguration(DefaultConfiguration):
    """
    Configurations inheriting this class will be able to export a whole batch
    of files at once onto the destination server.

    Management command: python manage.py pigeon_mass_push <config_name>
    """

    _local_checksum = _remote_checksum = False  # --- Used in tests, to
                                                #      validate the export

    def get_items_to_push(self):
        """ Get the list of items to include in this push. Implement me! """
        return list()

    def add_files_to_export(self, export_dir):
        """ Add files to export. Implement me! """
        pass

    def pack(self):
        """ Pack files to deliver, return a list of files. Implement me! """
        return list()

    def cleanup(self):
        """ Delete temporary files in export directory. """
        if os.path.exists(self.working_directory):
            shutil.rmtree(self.working_directory)

    def finalize_push(self):

        # --- Pack exported files
        files = self.pack()

        # --- Deliver newly-created archive to destination
        for push_url in self.push_urls:
            self.deliver(files, URL(push_url))

        # --- Cleanup the mess
        self.cleanup()

    @property
    def tmp_directory(self):
        """
        Relative directory to temporary store files in.

        **Must** be defined for archive pushers.
        """
        return ".work"


class ZIPPusherConfiguration(MassPusherConfiguration):
    """
    Configurations inheriting this class will be able to export a ZIP archive of
    a whole batch of files onto the destination server.
    """

    @property
    def archive_name(self):
        """
        Helper: build the filename of the ZIP archive to create.
        """
        return "%s.zip" % self.name

    def pack(self):
        """ Pack files into ZIP archive. """

        dirname = self.working_directory
        logging.debug("pack(): dirname: %s" % dirname)

        # --- Add files to export, if necessary
        self.add_files_to_export(dirname)

        zipname = os.path.join(
            self.root_directory,
            self.archive_name
        )
        logging.debug("pack(): zipname: %s" % zipname)

        try:
            zipdir(dirname, zipname)
        except IOError:
            logging.error(u"pack(): Cannot create archive '%s' in directory '%s'" \
                % (zipname, dirname))
            raise
        except Exception, e:
            message = u"pack(): Exception during archive creation. "
            message += u'Exception ``%s`` raised: %s ' \
                % (e.__class__.__name__, e.message)
            logging.error(message, exc_info=True)
            raise

        self._archive_name = os.path.basename(zipname)
        logging.debug("pack(): archive_name: %s" % self._archive_name)

        self._local_checksum = TreeHash(dirname).hash()
        logging.debug("pack(): local_checksum: %s" % self._local_checksum)

        return [zipname]


class TARPusherConfiguration(MassPusherConfiguration):
    """ Later...? """
    pass


class DirectoryPusherConfiguration(MassPusherConfiguration):
    """ Later...? """
    pass
