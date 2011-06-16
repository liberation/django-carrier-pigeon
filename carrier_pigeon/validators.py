# -*- coding: utf-8 -*-
"""
Validators are made to validate ouput. Validators must raise Exception if the
output do not validate.
"""

from xml.parsers.expat import ParserCreate


def wellformed_xml_validator(output):
    """
    This check only the well-formedness.
    It's not a DTD based validation.
    """
    parser = ParserCreate("utf-8")
    # parser will raise an Exception if the output is not wellformed
    parser.Parse(output)
    return True
