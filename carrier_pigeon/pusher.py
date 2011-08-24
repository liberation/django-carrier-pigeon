import os
import logging
from ftplib import FTP, error_perm

from carrier_pigeon.models import ItemToPush

logger = logging.getLogger('carrier_pigeon.pusher')


def ftp_send(row, url, file_path):
    """Sends the file by ftp using information found in url."""
    try:
        ftp = FTP(timeout=30)
        ftp.connect(url.domain, url.port)

        if url.login:
            ftp.login(url.login, url.password)
        else:
            ftp.login()

        # Path should not end with a /
        path = url.path
        if path.endswith("/"):
            path = url.path[:-1]
        # Go to remote directory (create it if needed)
        for directory in path.split("/"):
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
        f = open(file_path)
        ftp.storbinary('STOR %s' % filename, f)
        ftp.close()
        ftp.quit()
        f.close()
        logger.debug('successfully pushed %s@%s' % (filename, url.url))
        return True
    except Exception, e:
        row.status = ItemToPush.STATUS.SEND_ERROR
        row.message = 'ftp_send: exception message: %s' % (e.message)
        row.save()
        return False

def dummy_send(row, url, file_path):
    """
    Dummy sender to use for tests and developpement phases.
    """
    return True

def send(row, url, file_path):
    """dispactch send according to url scheme"""
    if url.scheme == 'ftp':
        return ftp_send(row, url, file_path)
    if url.scheme == 'dummy':
        return dummy_send(row, url, file_path)
    logger.error('url scheme %s not supported' % url.scheme)

