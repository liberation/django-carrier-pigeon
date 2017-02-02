# -*- coding:utf-8 -*-

import os
import os.path
import logging
from datetime import datetime

from abc import abstractmethod
from ftplib import FTP, error_perm

# FTP_TLS is not in py2.6
try:
    from ftplib import FTP_TLS
except:
    from carrier_pigeon.lib.ftplib import FTP_TLS

import paramiko

from django.conf import settings
from django.template.defaultfilters import date as format_date

from carrier_pigeon.models import ItemToPush


logger = logging.getLogger('carrier_pigeon.sender')


class DefaultSender(object):

    def __init__(self, configuration):
        self.configuration = configuration

    @abstractmethod
    def _send_file(self, file_path, target_url, row=None):
        """ Send one file to destination. Implement me! """
        pass

    def deliver(self, file_list, target_url, row=None):
        """
        Deliver file(s) to destination.

        `configuration_root` is used to keep the files tree.
        """

        ok = True
        max_ = settings.CARRIER_PIGEON_MAX_PUSH_ATTEMPTS

        for f in file_list:

            # --- 1. Send file

            sent = False
            for push_att_num in xrange(max_):
                logger.debug(u"'%s': push attempt #%s" % (f, push_att_num + 1))
                try:
                    sent = self._send_file(f, target_url, row)
                    break
                except Exception, ex:
                    pass

            # --- 2. Log delivery feedback

            now = format_date(datetime.now(), settings.DATETIME_FORMAT)

            if sent:
                feedback = u"[%s] '%s': push SUCCESS" % (now, f)
                logger.info(feedback)
            else:
                feedback = u"[%s] '%s': push ERROR: %s TARGET: %s" % (
                    now, f, ex, target_url.domain
                )
                logger.error(feedback)
                ok = False

            if row:
                row.message = feedback
                row.status = ItemToPush.STATUS.PUSHED if sent \
                    else ItemToPush.STATUS.SEND_ERROR
                row.save()

        return ok

    def get_relative_directory_for_file(self, file_path):
        """
        Get the place in the files tree where to push the file remotely.
        """
        if not file_path.startswith(self.configuration.outbox_directory):
            raise ValueError("Files must be stored in the configuration directory.")
        relative_path = file_path[len(self.configuration.outbox_directory):]
        path_elements = os.path.split(relative_path)
        if len(path_elements) > 1:
            relative_dir = path_elements[0]
        else:
            relative_dir = ""
        if relative_dir.startswith("/"):
            relative_dir = relative_dir[1:]  # It must be relative...
        return relative_dir


class DummySender(DefaultSender):

    def _send_file(self, row, url, file_path):
        """ Do nothing :) """
        return True


class FTPSender(DefaultSender):
    ftp_class = FTP

    def _connect(self, file_path, target_url):
        ftp = self.ftp_class(timeout=30)
        ftp.connect(target_url.domain, target_url.port)
        logging.debug(u"_send_file(): connected to %s on port %s" %
                      (target_url.domain, target_url.port if target_url.port \
                           else u"[default]"))

        ftp.login(target_url.login, target_url.password)
        logging.debug(u"_send_file(): logged in")

        return ftp

    def _send_file(self, file_path, target_url, row=None):
        """ Send the file by FTP using information found in url. """

        ftp = self._connect(file_path, target_url)

        target_path = os.path.join(
            target_url.path,
            self.get_relative_directory_for_file(file_path)
        )
        logging.debug(u"_send_file(): target_path: %s" % target_path)

        # Go to remote directory (create it if needed)
        for directory in target_path.split("/"):
            try:
                ftp.cwd(directory)
                # permanent error, in case the directory does not exist
                # ftplib raise a "generic" error_perm
            except error_perm:
                ftp.mkd(directory)
                # Don't catch the error now, in case the error_perm was for
                # another reason
                ftp.cwd(directory)

        filename = os.path.split(file_path)[1]
        logging.debug(u"_send_file(): filename: %s" % filename)

        f = open(file_path)
        ftp.storbinary('STOR %s' % filename, f)
        logging.debug(u"_send_file(): push ok")

        f.close()
        ftp.quit()
        logging.debug(u"_send_file(): disconnected")

        return True


class FTPSSender(FTPSender):
    ftp_class = FTP_TLS

    def _connect(self, file_path, target_url):
        ftp = super(FTPSSender, self)._connect(file_path, target_url)
        ftp.prot_p()
        return ftp


class SFTPSender(DefaultSender):

    def _connect(self, file_path, target_url):
        self.client = paramiko.SSHClient()

        self.client.set_missing_host_key_policy(paramiko.MissingHostKeyPolicy())

        self.client.connect(
            target_url.domain,
            port=target_url.port if target_url.port else 22,
            username=target_url.login,
            password=target_url.password
        )

        sftp = self.client.open_sftp()
        sftp.chdir('.')

        return sftp

    def _send_file(self, file_path, target_url, row=None):
        sftp = self._connect(file_path, target_url)

        target_path = os.path.join(
            sftp.getcwd() + target_url.path,
            self.get_relative_directory_for_file(file_path)
        )

        logging.debug(u"_send_file(): target_path: %s" % target_path)

        try:
            sftp.mkdir(target_path)
        except:
            logging.debug(u"_send_file(): target_path already exists")

        filename = os.path.split(file_path)[1]
        logging.debug(u"_send_file(): filename: %s" % filename)

        sftp.put(file_path, os.path.join(target_path, filename))
        logging.debug(u"_send_file(): push ok")

        sftp.close()

        return True
