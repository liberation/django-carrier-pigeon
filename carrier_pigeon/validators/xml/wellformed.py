# -*- coding: utf-8 -*-

from xml.parsers.expat import ParserCreate

from carrier_pigeon.validators.base import BaseValidator


class WellformedXmlValidator(BaseValidator):
    """
    This check only the well-formedness.
    It's not a DTD based validation.
    """

    def validate(self):
        parser = ParserCreate("utf-8")
        # parser will raise an Exception if the output is not wellformed
        parser.Parse(self.output)
        return True
