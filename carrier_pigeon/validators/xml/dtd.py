# -*- coding: utf-8 -*-

from lxml import etree

from carrier_pigeon.validators.base import BaseValidator


class DtdXmlValidator(BaseValidator):
    """
    Validate an XML against a DTD.
    """

    def validate(self):
        """
        You must define a MyOutputMaker.dtd property to use this validator.
        
        This property must contain the absolute path to the dtd to use.
        """
        dtd = etree.DTD(open(self.outputmaker.dtd, 'rb'))
        xml = etree.XML(self.output)
        return dtd.validate(xml)
