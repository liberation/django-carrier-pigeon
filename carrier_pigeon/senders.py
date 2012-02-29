# -*- coding:utf-8 -*-

import os
import logging
from abc import abstractmethod
from ftplib import FTP, error_perm
from datetime import datetime

from django.conf import settings
from django.template.defaultfilters import date as format_date

from carrier_pigeon.models import ItemToPush


logger = logging.getLogger('carrier_pigeon.sender')


class DefaultSender(object):

    @abstractmethod
    def _send_file(self, file_path, target_url, row=None):
        """ Send one file to destination. Implement me! """
        pass

    def deliver(self, file_list, target_url, row=None):
        """ Deliver file(s) to destination. """

        ok = True
        max_ = settings.CARRIER_PIGEON_MAX_PUSH_ATTEMPTS

        for f in file_list:
            
            # --- 1. Send file

            sent = False
            for push_att_num in xrange(max_):
                logger.debug("'%s': push attempt #%s" % (f, push_att_num + 1))
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
                feedback = u"[%s] '%s': push ERROR: %s" % (now, f, ex)
                logger.error(feedback)
                ok = False

            if row:
                row.message = feedback
                row.status = ItemToPush.STATUS.PUSHED if sent \
                    else ItemToPush.STATUS.SEND_ERROR
                row.save()

        return ok


class DummySender(DefaultSender):

    def _send_file(self, row, url, file_path):
        """ Do nothing :) """
        return True


class FTPSender(DefaultSender):

    def _send_file(self, file_path, target_url, row=None):
        """ Send the file by FTP using information found in url. """

        ftp = FTP(timeout=30)
        ftp.connect(target_url.domain, target_url.port)
        logging.debug(u"_send_file(): connected to %s on port %s"
            % (target_url.domain, target_url.port if target_url.port \
                 else u"[default]"))

        if target_url.login:
            ftp.login(target_url.login, target_url.password)
        else:
            target_url.login()
        logging.debug(u"_send_file(): logged in")
        
        # Path should not end with a /
        target_path = target_url.path
        if target_path.endswith("/"):
            target_path = target_url.path[:-1]
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

# FIXME make it customisable
SENDER_MAPPING = {
    'ftp': FTPSender,
    'dummy': DummySender,
}
