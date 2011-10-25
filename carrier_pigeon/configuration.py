# -*- coding:utf-8 -*-

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
from utils import URL, join_url_to_directory, zipdir, \
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
        """ A list a function that takes the content the content of the file
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

    def get_extra_context(self, instance):
        return dict()

    def get_output_filename(self, instance):
        return '%s_%s_%s.xml' % (instance._meta.app_label.lower(),
                                 instance._meta.module_name,
                                 instance.pk)

    def get_binary_path(self, instance):
        return '%s_%s' % (instance._meta.module_name, instance.pk)

    def output(self, instance):
        rule_name = self.name

        # build template file path
        app_label = instance._meta.app_label.lower()
        class_name = instance._meta.module_name
        template_name = '%s_%s.xml' % (app_label, class_name)

        template_path = 'carrier_pigeon/%s/%s' % (rule_name, template_name)

        template = loader.get_template(template_path)

        context = self.get_extra_context(instance)
        context['object'] = instance
        context = Context(context)
        output = template.render(context)
        return output.encode("utf-8")

    def instance_binaries(self, instance, depth):
        binaries = list()

        for field in instance._meta.fields:

            if is_file_field(field):
                binaries.append(field.path)

            elif is_relation_field(field) and depth:
                for obj in related_objects(instance, field):
                    binaries.extend(self.instance_binaries(obj, depth-1))

        return binaries

    def output_binaries(self, instance):
        """ Output all `instance`'s linked binaries. Return file list. """

        if not self.EXPORT_BINARIES:
            return list()

        depth = self.EXPORT_BINARIES_RELATIONSHIP_DEPTH \
            if self.EXPORT_BINARIES_ACROSS_RELATIONSHIPS else 0

        return self.instance_binaries(instance, depth)

    def post_select(self, instance):
        pass

    def initialize_push(self):
        pass

    def export_item(self, item, row=None):
        rule_name = self.name

        output_files = []

        # --- Build output
        try:
            output = self.output(item)
        except Exception, e:
            message = u"Exception during output generation. "
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
                message = u"Validation ``%s`` failed ! " % validator.__name__
                message += u'Catched exception %s : %s' % (
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
            binary_path = '%s/%s' % (
                output_directory, self.get_binary_path(item))
            for binary in binaries:
                try:
                    shutil.copy(binary, binary_path)
                    output_files.append(
                        '%s/%s' % binary_path, os.path.basename(binary))
                except:
                    logging.error(
                        'export_item(): Error while copying %s to %s'
                            % (binary, binary_path))

        return output_files

    def finalize_push(self):
        pass


class SequentialPusherConfiguration(DefaultConfiguration):
    """
    Configurations inheriting this class will send their files onto the
    destination server one by one, progressively.

    Associated management command: python manage.py pigeon_push
    """

    # --- Should the linked binaries be exported as well?
    EXPORT_BINARIES = False

    # --- Should we look for binaries across relationships?
    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = False

    # --- If so, across how many relationship levels?
    EXPORT_BINARIES_RELATIONSHIP_DEPTH = 3


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

    # --- Should the linked binaries be exported as well?
    EXPORT_BINARIES = True

    # --- Should we look for binaries across relationships?
    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = False

    # --- If so, across how many relationship levels?
    EXPORT_BINARIES_RELATIONSHIP_DEPTH = 3


    def get_items_to_push(self):
        """ Get the list of items to include in this push. Implement me! """
        return list()
        
    def pack(self):
        """ Pack files to deliver, return a list of files. Implement me! """
        return list()

    def finalize_push(self):
        files = self.pack()
        target_url = URL(self.TARGET_URL)
        return self.deliver(files, target_url)


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
        zipname = self._get_archive_name()

        try:
            zipdir(dirname, zipname)
        except IOError:
            logger.error(u"pack(): Cannot create archive '%s' in directory '%s'" \
                % (zipname, dirname))
            raise
        except Exception, e:
            message  = u"pack(): Exception during archive creation. "
            message += u'Exception ``%s`` raised: %s ' \
                % (e.__class__.__name__, e.message)
            logger.error(message, exc_info=True)
            raise

        return [zipname]


class TARPusherConfiguration(MassPusherConfiguration):
    """ Later...? """
    pass


class DirectoryPusherConfiguration(MassPusherConfiguration):
    """ Later...? """
    pass 
