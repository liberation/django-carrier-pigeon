# -*- coding:utf-8 -*-

"""
Packers are classes responsable of preparing the files for the pusher.
TODO: make the packer configurable per push url.
"""
import os
import shutil
import logging

from carrier_pigeon.utils import zipdir

logger = logging.getLogger('carrier_pigeon.packer')


class BasePacker(object):

    def __init__(self, configuration, files):
        self.configuration = configuration
        self.files = set(files)

    def pack(self, files):
        raise NotImplementedError()

    def get_tmp_relative_file_name(self, file_path):
        return file_path[len(self.configuration.tmp_directory)+1:]


class FlatPacker(BasePacker):
    """
    Do not pack, keep files as they are.
    """

    def pack(self):
        """
        Just returns files.
        """
        outbox_files = []
        for f in self.files:
            outbox_file_path = os.path.join(
                                  self.configuration.outbox_directory,
                                  self.get_tmp_relative_file_name(f)
                              )
            # We are not shure the relative folders already exists in outbox
            full_outbox_path = os.path.split(outbox_file_path)[0]
            if not os.path.exists(full_outbox_path):
                os.makedirs(full_outbox_path)
            shutil.move(f, outbox_file_path)
            outbox_files.append(outbox_file_path)
        return outbox_files


class ZIPPacker(BasePacker):
    """
    Pack outputed files in a ZIP.
    """

    @property
    def archive_name(self):
        if hasattr(self.configuration, "archive_name"):
            return self.configuration.archive_name
        else:
            return "%s.zip" % self.configuration.name

    def pack(self):
        """ Pack files into ZIP archive. """

        dirname = self.configuration.tmp_directory
        logging.debug("pack(): dirname: %s" % dirname)

        if not os.path.exists(self.configuration.outbox_directory):
            os.makedirs(self.configuration.outbox_directory)

        zipname = os.path.join(
            self.configuration.outbox_directory,
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

        return [zipname]


class TARPacker(BasePacker):
    """ Later...? """
    pass
