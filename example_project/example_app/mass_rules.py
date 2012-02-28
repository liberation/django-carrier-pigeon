# -*- coding:utf-8 -*-

import shutil
import datetime

from carrier_pigeon.configuration import ZIPPusherConfiguration
from carrier_pigeon.linkers import StandardBinaryLinker
from carrier_pigeon.senders import FTPSender


class OtherPartner(ZIPPusherConfiguration, StandardBinaryLinker, FTPSender):

    def get_items_to_push(self):
        """ Export all articles published during the previous week. """

        now = datetime.datetime.now()
        one_week_ago = now - datetime.timedelta(days=7)
        items = Story.objects.all(updating_date__gt=one_week_ago)
        return items


#class PQHR(ZIPPusherConfiguration, StandardBinaryLinker, FTPSender):

#    EXPORT_BINARIES = True
#    EXPORT_BINARIES_FIELDS = []
#    EXPORT_BINARIES_ACROSS_RELATIONSHIPS = True
#    EXPORT_BINARIES_RELATIONSHIP_DEPTH = 2

#    _publication = None
#    _books = list()
#    _pages = list()
#    _articles = list()

#    def get_template_name(self, instance):
#        return 'libe_article.xml'

#    def get_template_path(self, instance):
#        return 'pqhr/%s' % self.get_template_name(instance)

#    def get_items_to_push(self):
#        """ Select all articles of today's Publication.
#        Also fetch its related Books and PaperPages while we're there. """

#        today = datetime.datetime.now()

#        try:
#            self._publication = Publication.objects.filter(
#                paper_publication_date=today)[0]        
#        except IndexError:  
#            logging.info("No Publication found today, exiting.")
#            return list()

#        self._books = self._publication.get_books()
#            
#        for book in self._books:
#            for page in book.get_pages():
#                self._pages.append(page)
#        self._pages = list(set(self._pages))

#        self._articles = self._publication.get_ordered_articles()

#        return self._articles

#    def add_files_to_export(self, export_dir):
#        """ Add PDFs of today's Publication to the export directory.  """

#        for page in self._pages:
#            try:
#                pdf_path = page.original_file.path
#                logging.debug(u"Adding '%s' for Page #%d" % (pdf_path, page.id))
#                shutil.copy(pdf_path, export_dir)
#                logging.debug(u"  OK")

#            except ValueError:
#                logging.info(
#                    u"No PDF for Page with ID %d, skipping." % (page.id,))                
#                continue

#            except IOError:
#                logging.error(
#                    u"Can't find PDF file '%s' for Page with ID %d, skipping."
#                        % (pdf_path, page.id))                
