# -*- coding:utf-8 -*-

import os
import os.path
import shutil
import logging

from django.conf import settings

from carrier_pigeon.models import ItemToPush
from carrier_pigeon.senders import DummySender, FTPSender, FTPSSender
from carrier_pigeon.utils import URL


logger = logging.getLogger('carrier_pigeon.configuration')


class DefaultConfiguration(object):
    """
    Abstract class for all configuration types.
    
    You must inherit from it to create a new type, but not when using carrier pigeon.
    For this, you have to inherit one of the two types already existing:
    - SequentialPusherConfiguration
    - ZIPPusherConfiguration
    """

    SENDER_MAPPING = {
        'ftp': FTPSender,
        'ftps': FTPSSender,
        'dummy': DummySender,
    }

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
    def tmp_directory(self):
        """
        Effective directory where the file are stored by the OutputMakers.
        """
        return os.path.join(
            self.root_directory,
            "tmp",
        )

    @property
    def outbox_directory(self):
        """
        Effective directory where the file are stored by the Packers.
        """
        return os.path.join(
            self.root_directory,
            "outbox",
        )

    def output_files_from_item(self, item, row=None):
        """
        Export one item. Main entry point of this class's methods.

        `item` is a content to push
        `row` is the optionnal correspondant ItemToPush instance
        (only for sequential mode).
        
        Could be recursive if item as related_items.
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
                logger.info("Error for item %i with Output Maker %s"
                            % (item.pk, output_maker))
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
                        logger.info("Validation error for item %i with"
                                    " validator %s"
                                    % (
                                        item.pk,
                                        validator_class
                                    ))
                        break  # escape from first for loop

                if not validation:  # --- If one validator did not pass we
                                    #      do no want to send the file
                    logger.info("the output was not validated for item : %i"
                                % item.pk
                                )
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
                logger.info("File added to output: %s" % local_final_path)
                output_files.append(local_final_path)

        # --- Manage related items, if any
        for related_item in supervisor.get_related_items():
            related_files = self.output_files_from_item(related_item, row)
            output_files += related_files

        return output_files

    def process_item(self, item, row=None):
        """
        Called for each entry item.
        
        Which means one time for sequential pusher, many times for mass pusher.
        """
        return self.output_files_from_item(item, row)

    def pack(self, files):
        if not files:
            pass # must stop process here
        packer = self.packer(self, files)
        return packer.pack()

    def cleanup(self):
        """ Delete temporary files in export directory. """
        if os.path.exists(self.tmp_directory):
            shutil.rmtree(self.tmp_directory)

    def finalize_push(self, files, row):
        """
        Called one time per push.
        """
        raise NotImplementedError()

    def deliver(self, files, target_url, row=None):
        """Defines from url scheme the right sender to use, and calls it."""
        try:
            sender_class = self.SENDER_MAPPING[target_url.scheme]
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

    def finalize_push(self, files, row):
        """
        Send packed files to row.push_url.
        """

        # --- Pack exported files
        files = self.pack(files)

        target_url = row.push_url
        logger.debug('export_item(): target url: ``%s``' % target_url)
        target_url = URL(target_url)

        self.deliver(files, target_url, row)

        # --- Cleanup the mess
        self.cleanup()


class MassPusherConfiguration(DefaultConfiguration):
    """
    Configurations inheriting this class will be able to export a whole batch
    of files at once onto the destination server.

    Management command: python manage.py pigeon_mass_push <config_name>
    """

    def get_items_to_push(self):
        """ Get the list of items to include in this push. Implement me! """
        return list()

    def finalize_push(self, files, row=None):
        """
        Send packed files one time per push url.
        """

        # --- Pack exported files
        files = self.pack(files)

        # --- Deliver newly-created archive to destination
        for push_url in self.push_urls:
            self.deliver(files, URL(push_url))

        # --- Cleanup the mess
        self.cleanup()
