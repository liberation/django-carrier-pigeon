# -*- coding: utf-8 -*-

from lxml import etree

from carrier_pigeon.validators.base import BaseValidator


class SchemaXmlValidator(BaseValidator):
    """
    Validate an XML against a schema (XSD).
    """

    def validate(self):
        """
        You must define a MyOutputMaker.xsd property to use this validator.
        
        This property must contain the absolute path to the schema to use.
        """
        with open(self.outputmaker.xsd) as f:
            schema_doc = etree.parse(f)
            xsd = etree.XMLSchema(schema_doc)
            xml = etree.XML(self.output)
            # assertValid will raise an exception if xml is not valid
            xsd.assertValid(xml)
            return True
