# -*- coding:utf-8 -*-

import logging
import datetime

from abc import abstractmethod

from django.template import Context
from django.template import loader
from django.template.base import TemplateDoesNotExist

from django.conf import settings

from carrier_pigeon.models import ItemToPush
from carrier_pigeon.facility import add_item_to_push
from carrier_pigeon.pusher import send
from carrier_pigeon.utils import URL, join_url_to_directory, zipdir
from carrier_pigeon import REGISTRY


logger = logging.getLogger('carrier_pigeon.configuration')


class DefaultConfiguration:
    """This is an abstract class that you must inherit in your projet
    to create a configuration. By default this configuration try to
    build an xml file from a template see ``get_output_filename`` and
    ``output`` methods for more information."""

    @property
    def name(self):
        return self.__class__.__name__.lower()

    @property
    def push_urls(self):
        """Remote locations urls where to push content."""
        try:
            return settings.CARRIER_PIGEON_PUSH_URLS[self.name]
        except (AttributeError, KeyError):
            logger.warning(u'No push url setted for rule "%s"' % self.name)
            return []

    @property
    def validators(self):
        """A list a function that takes the content the content of the file
        that will be pushed."""
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

    def post_select(self, instance):
        pass

    def initialize_push(self):
        pass

    def export_one(self, item, row=None):
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
        
        # Get target directory
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

        # Build output file path for archiving
        output_directory = settings.CARRIER_PIGEON_OUTPUT_DIRECTORY
        output_directory += '/%s/' % rule_name
        output_directory += '/%s/' % target_directory

        # Create output directory if necessary
        if not os.path.exists(output_directory):
            os.makedirs(output_directory)
        output_path = '%s/%s' % (output_directory, output_filename)

        # Write output file
        f = open(output_path, 'w')
        f.write(output)
        f.close()
        output_files.append(output_path)

        return output_files

    def finalize_push(self):
        pass


class FilesPusherConfiguration(DefaultConfiguration):
    """
    Configurations inheriting this class will send their files onto the
    destination server one by one, progressively.

    Associated management command: python manage.py pigeon_push
    """

    def export_one(self, item):
        """ Here, `item` is an `ItemToPush` instance. """

        row = item
        item = row.content_object
        files = super(FilesPusherConfiguration, self).export_one(self, item, row)
            
        # --- Prepare sending
        target_url = join_url_to_directory(row.push_url, target_directory)
        logger.debug('export_one(): target url: ``%s``' % target_url)
        target_url = URL(target_url)

        # --- Try to send the file(s)
        fail = False
        max_ = settings.CARRIER_PIGEON_MAX_PUSH_ATTEMPTS
        for f in files:
            for push_attempt_num in xrange(max_):

                logger.debug('export_one(): Push attempt #%s' % push_attempt_num)
                row.push_attempts += 1
                row.last_push_attempts_date = datetime.now()
                row.save()

                if not send(row, target_url, f):
                    fail = True

        if not fail:
            # --- Mark this row as successfully pushed
            row.status = ItemToPush.STATUS.PUSHED
            row.save()
            logger.debug('export_one(): Huge success!')

        return not fail


class ArchivePusherConfiguration(DefaultConfiguration):
    """
    Configurations inheriting this class will first archive all their files
    into a ZIP archive and _then_ send this archive onto the destination server.
    
    Associated management command: python manage.py pigeon_zipush <config_name>
    """

    rows = []

    @abstractmethod
    def get_items_to_push(self):
        """ Get the list of items to include in this push. Implement me! """
        pass

    def get_export_root_directory(self):
        """ Build the name of the directory to zip. Override me! """
        
        return '%s/%s' % (
            settings.CARRIER_PIGEON_OUTPUT_DIRECTORY,
            self.name,
        )

    def get_archive_name(self):
        """ Build the filename of the zip archive to create.  Override me! """
        now = datetime.datetime.now()
        
        return '%s/%s_%s.zip' % (
            settings.CARRIER_PIGEON_OUTPUT_DIRECTORY,
            self.name,
            now.strftime(settings.CARRIER_PIGEON_TIMESTAMP_FORMAT)
        )
        
    def finalize_push(self):

        # --- Build the ZIP archive
        directory_name = self.get_export_root_directory()
        archive_name = self.get_archive_name()

        try:
            zipdir(directory_name, archive_name)
        except IOError:
            logger.error(u"finalize_push(): I/O error: cannot create archive '%s' in directory '%s'" \
                % (archive_name, directory_name))
            raise
        except Exception, e:
            message  = u"finalize_push(): Exception during archive creation. "
            message += u'Exception ``%s`` raised: %s ' \
                % (e.__class__.__name__, e.message)
            logger.error(message, exc_info=True)
            raise

        # --- Send it
        sent = False
        max_ = settings.CARRIER_PIGEON_MAX_PUSH_ATTEMPTS

        for push_attempt_num in xrange(max_):
            logger.debug('finalize_push(): Push attempt #%s' % push_attempt_num)
            if send(archive_name, target_url, output_path):
                sent = True
                break

        if sent:
            # Cleanup...
            pass

        else:
            logger.error(u"finalize_push(): Send failed for '%s' after %d attempts" \
                % (archive_name, max_))
