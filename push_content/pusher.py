import os
import logging
from ftplib import FTP

from push_content.models import ItemToPush

logger = logging.getLogger('push_content.pusher')


def ftp_send(row, url, file_path):
    """Sends the file by ftp using information found in url."""
    try:
        ftp = FTP()
        ftp.connect(url.domain, url.port)

        if url.login:
            ftp.login(url.login, url.password)
        else:
            url.login()

        ftp.cwd(url.path)
        filename = os.path.split(file_path)[1]
        f = open(file_path)
        ftp.storbinary('STOR %s' % filename, f)
        f.close()
        ftp.quit()
        logger.debug('successfully pushed %s@%s' % (filename, url.url))
        return True
    except Exception, e:
        row.status = ItemToPush.STATUS.SEND_ERROR
        row.message = '%s, exception message: %s' % ('ftp_send: ',
                                                      e.message)
        row.save()
        return False


def send(row, url, file_path):
    """dispactch send according to url scheme"""
    if url.scheme == 'ftp':
        return ftp_send(row, url, file_path)
    logger.error('url shceme %s not supported' % url.scheme)
