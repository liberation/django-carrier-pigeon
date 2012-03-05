"""
Validators are made to validate ouput. Validators must raise Exception if the
output do not validate. They must implement the `validate` method.
"""


class BaseValidator(object):

    def __init__(self, output, outputmaker):
        """
        `output` is the content to validate.
        `outputmaker` is the active OutputMaker class, that can be used to
        configure the validator.
        """
        self.output = output
        self.outputmaker = outputmaker

    def validate(self):
        raise NotImplementedError('Implement me!')
