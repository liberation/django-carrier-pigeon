# -*- coding:utf-8 -*-

import os
import shutil
import logging

from abc import abstractmethod
from datetime import datetime

from django.conf import settings
from django.template import Context
from django.template import loader
from django.template.base import TemplateDoesNotExist

from carrier_pigeon import REGISTRY

from models import ItemToPush
from facility import add_item_to_push
from senders import DefaultSender, FTPSender
from utils import URL, TreeHash, join_url_to_directory, zipdir, \
    is_file_field, is_relation_field, related_objects


logger = logging.getLogger('carrier_pigeon.configuration')


class DefaultConfiguration:
    """ This is an abstract class that you must inherit in your project
    to create a configuration. By default this configuration try to
    build an xml file from a template see ``get_output_filename`` and
    ``output`` methods for more information. """

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

    @property
    def validators(self):
        """ A list of functions that validate the contents of the file
        that will be pushed. """
        return list()

    @abstractmethod
    def filter_by_instance_type(self, instance):
        pass

    @abstractmethod
    def filter_by_updates(self, instance):
        pass

    @abstractmethod
    def filter_by_state(self, instance):
        pass

    @abstractmethod
    def get_directory(self, instance):
        pass

    def get_template_name(self, instance):
        """ Return the name of the template used to dump the object data. """

        app_label = instance._meta.app_label.lower()
        class_name = instance._meta.module_name
        template_name = '%s_%s.xml' % (app_label, class_name)

    def get_template_path(self, instance):
        """ Return the fully-qualified path to the template used to dump
        the object data. """

        rule_name = self.name
        template_name = self.get_template_name(instance)
        return 'carrier_pigeon/%s/%s' % (rule_name, template_name)

    def get_extra_context(self, instance):
        """ If there needs to be some extra context passed to the template,
        just override this method in your own configuration implementation. """

        return dict()

    def get_output_filename(self, instance):
        """ Return the filename used to dump the object data. """

        return '%s_%s_%s.xml' % (instance._meta.app_label.lower(),
                                 instance._meta.module_name,
                                 instance.pk)

    def get_binary_path(self, instance):
        """ Return the path into which to store the item's related
        binary files. """

        return '%s_%s' % (instance._meta.module_name, instance.pk)

    def item_binaries(self, item, depth):
        """ Return the list of binary files linked to this item, by
        listing file-like fields on this item and its related ones.
        Should be implemented in a Linker module. """

        return list()

    def output_binaries(self, item):
        """ Output all `item`'s linked binaries. Return file list.
        Should be implemented in a Linker module. """

        return list()

    def output(self, instance):
        """ Dump this instance's data into an UTF-8 string. """

        template_path = self.get_template_path(instance)
        template = loader.get_template(template_path)

        context = self.get_extra_context(instance)
        context['object'] = instance
        context = Context(context)

        output = template.render(context)
        return output.encode("utf-8")


    def post_select(self, instance):
        pass

    def initialize_push(self):
        """ Right here, it's nothing more than a placeholder, but you may use
        this method in your subclass if you need a hook to execute some code
        before looping on the items to export. """

        pass

    def export_item(self, item, row=None):
        """ Export one item. Main entry point of this class's methods. """

        rule_name = self.name

        output_files = []

        # --- Build output
        try:
            output = self.output(item)
        except Exception, e:
            message  = u"Exception during output generation. "
            message += u'Exception ``%s`` raised: %s ' % (
                            e.__class__.__name__, e.message)
            if row:
                row.status = ItemToPush.STATUS.OUTPUT_GENERATION_ERROR
                row.message = message
                row.save()
            logger.error(message, exc_info=True)
            raise

        # --- Validate output
        validation = True
        for validator in self.validators:
            try:
                validator(output)
                logger.debug('validation ``%s`` passed successfully'
                                                       % validator.__name__)
            except Exception, e:
                validation = False
                message  = u"Validation ``%s`` failed ! " % validator.__name__
                message += u'Caught exception %s : %s' % (
                            e.__class__.__name__, e.message)
                if row:
                    row.status = ItemToPush.STATUS.VALIDATION_ERROR
                    if row.message != None:
                        row.message += '\n' + message
                    else:
                        row.message = message
                    row.save()
                logger.error(message, exc_info=True)

        if not validation:  # --- If one validator did not pass we
                            #      do no want to send the file
            logger.debug('the output was not validated')
            raise
        
        output_filename = self.get_output_filename(item)
        
        # --- Get target directory
        target_directory = None
        try:
            target_directory = self.get_directory(item)
        except Exception, e:
            message = u"Error during ``get_directory``. "
            message += u"%s: %s" % (
                            e.__class__.__name__, e.message)
            if row:
                row = ItemToPush(rule_name=rule_name,
                                 content_object=instance)
                row.status = ItemToPush.STATUS.GET_DIRECTORY_ERROR
                row.message = message
                row.save()
            logger.error(message, exc_info=True)
            raise

        # --- Build output file path for archiving
        output_directory = settings.CARRIER_PIGEON_OUTPUT_DIRECTORY
        output_directory += '/%s/' % rule_name
        if target_directory:
            output_directory += '/%s/' % target_directory

        # --- Create output directory if necessary
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        output_path = '%s/%s' % (output_directory, output_filename)

        # --- Write output file
        f = open(output_path, 'w')
        f.write(output)
        f.close()
        output_files.append(output_path)

        # --- Add linked binaries, if any
        binaries = self.output_binaries(item)
        if binaries:
            bin_dir = '%s%s' % (output_directory, self.get_binary_path(item))
            try:
                os.makedirs(bin_dir)
                logging.debug('export_item(): created dir: %s' % bin_dir)
            except:
                pass

            # --- Copy all binary files to the output directory
            for binary in binaries:
                try:
                    bin_path = os.path.join(bin_dir, os.path.basename(binary))
                    shutil.copy(binary, bin_path)
                    output_files.append(
                        '%s/%s' % (bin_dir, os.path.basename(binary)))
                    logging.info(
                        'export_item(): Copy successful: %s to %s'
                            % (binary, bin_path))

                except Exception, ex:
                    logging.error(
                        'export_item(): Error while copying %s to %s: %s'
                            % (binary, bin_path, ex))

        return output_files

    def finalize_push(self):
        """ Right here, it's nothing more than a placeholder, but you may use
        this method in your subclass if you need a hook to execute some code
        after looping on the items to export. For example, if the exported
        files need to be archived and sent, this will happen here. """

        pass


class SequentialPusherConfiguration(DefaultConfiguration):
    """
    Configurations inheriting this class will send their files onto the
    destination server one by one, progressively.

    Associated management command: python manage.py pigeon_push
    """

    EXPORT_BINARIES = False
    EXPORT_BINARIES_FIELDS = None
    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = False
    EXPORT_BINARIES_RELATIONSHIP_DEPTH = 0

    def export_item(self, item):
        """ Here, `item` is an `ItemToPush` instance. """

        row = item
        item = row.content_object
        files = super(SequentialPusherConfiguration, self).export_item(self, item, row)
            
        target_url = join_url_to_directory(row.push_url, target_directory)
        logger.debug('export_item(): target url: ``%s``' % target_url)
        target_url = URL(target_url)

        return self.deliver(files, target_url, output_path, row)


class MassPusherConfiguration(DefaultConfiguration):
    """
    Configurations inheriting this class will be able to export a whole batch
    of files at once onto the destination server.
    
    Management command: python manage.py pigeon_mass_push <config_name>
    """

    EXPORT_BINARIES = True
    EXPORT_BINARIES_FIELDS = None
    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = False
    EXPORT_BINARIES_RELATIONSHIP_DEPTH = 3

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
        shutil.rmtree(self._get_export_root_directory())

    def finalize_push(self):

        # --- Pack exported files
        files = self.pack()

        # --- Deliver newly-created archive to destination
        target_url = URL(self.TARGET_URL)
        self.deliver(files, target_url)

        # --- Cleanup the mess
        self.cleanup()

class ZIPPusherConfiguration(MassPusherConfiguration):
    """
    Configurations inheriting this class will be able to export a ZIP archive of
    a whole batch of files onto the destination server.
    """

    def _get_export_root_directory(self):
        """ Helper: build the name of the directory to zip. """
        
        return '%s/%s' % (
            settings.CARRIER_PIGEON_OUTPUT_DIRECTORY,
            self.name,
        )

    def _get_archive_name(self):
        """ Helper: build the filename of the ZIP archive to create. """
        
        now = datetime.now()
        
        return '%s/%s_%s.zip' % (
            settings.CARRIER_PIGEON_OUTPUT_DIRECTORY,
            self.name,
            now.strftime(settings.CARRIER_PIGEON_TIMESTAMP_FORMAT)
        )

    def pack(self):
        """ Pack files into ZIP archive. """

        dirname = self._get_export_root_directory()
        logging.debug("pack(): dirname: %s" % dirname)

        # --- Add files to export, if necessary
        self.add_files_to_export(dirname)

        zipname = self._get_archive_name()
        logging.debug("pack(): zipname: %s" % zipname)

        try:
            zipdir(dirname, zipname)
        except IOError:
            logging.error(u"pack(): Cannot create archive '%s' in directory '%s'" \
                % (zipname, dirname))
            raise
        except Exception, e:
            message  = u"pack(): Exception during archive creation. "
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
