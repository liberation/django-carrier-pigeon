import logging

from django.template import Context
from django.template import loader
from django.template.base import TemplateDoesNotExist

from push_content.models import ItemToPush


logger = logging.getLogger('push_content.configuraiton')


class DefaultConfiguration:

    @property
    def push_urls(self):
        raise NotImplementedError()

    @property
    def validators(self):
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

    def output(self, row, instance):
        rule_name = row.rule_name

        # build template file path
        app_label = instance._meta.app_label.lower()
        class_name = instance._meta.module_name
        template_name = '%s_%s.xml' % (app_label, class_name)

        template_path = 'push_content/%s/%s' % (rule_name, template_name)

        # try to fetch template file
        try:
            template = loader.get_template(template_path)
        except TemplateDoesNotExist:
            message = 'Template %s does not exist' % template_path
            logger.error(message)
            row.status = ItemToPush.STATUS.TEMPLATE_NOT_FOUND
            row.message = message
            row.save()
            return None

        context = self.get_extra_context(instance)
        context['object'] = instance
        context = Context(context)
        output = template.render(context)
        return output

    def is_candidate(self, row):  # ItemToPush instance
        logger.debug('default is_candidate call: nothing done.')
