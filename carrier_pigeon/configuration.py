import logging

from django.template import Context
from django.template import loader
from django.template.base import TemplateDoesNotExist

from carrier_pigeon.models import ItemToPush


logger = logging.getLogger('push_content.configuration')


class DefaultConfiguration:
    """This is an abstract class that you must inherit in your projet
    to create a configuration. By default this configuration try to
    build an xml file from a template see ``get_output_filename`` and
    ``output`` methods for more information."""

    @property
    def push_urls(self):
        """Remote locations urls where to push content."""
        raise NotImplementedError()

    @property
    def validators(self):
        """A list a function that takes the content the content of the file
        that will be pushed."""
        return list()

    def filter_by_instance_type(self, instance):
        raise NotImplementedError()

    def filter_by_updates(self, instance):
        raise NotImplementedError()

    def filter_by_state(self, instance):
        raise NotImplementedError()

    def get_directory(self, instance):
        raise NotImplementedError()

    def get_extra_context(self, instance):
        return dict()

    def get_output_filename(self, instance):
        return '%s_%s.xml' % (instance._meta.app_label.lower(),
                              instance._meta.module_name)

    def output(self, instance):
        rule_name = self.name()

        # build template file path
        app_label = instance._meta.app_label.lower()
        class_name = instance._meta.module_name
        template_name = '%s_%s.xml' % (app_label, class_name)

        template_path = 'push_content/%s/%s' % (rule_name, template_name)

        template = loader.get_template(template_path)

        context = self.get_extra_context(instance)
        context['object'] = instance
        context = Context(context)
        output = template.render(context)
        return output

    def post_select(self, instance):
        pass

    def name(self):
        return self.__class__.__name__.lower()
