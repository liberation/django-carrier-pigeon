"""
    Configuration
    =============

    Carrier Pigeon tasks are managed with class as configuration,
    see :class:`~configuration.DefaultConfiguration` to get an idea
    of what is possible.
"""
import logging
from abc import abstractmethod

from django.template import Context
from django.template import loader
from django.template.base import TemplateDoesNotExist

from django.conf import settings

from carrier_pigeon.models import ItemToPush


logger = logging.getLogger('carrier_pigeon.configuration')


class DefaultConfiguration:
    """This is an abstract class that you must inherit in your projet
    to create a configuration. By default this configuration try to
    build an xml file from a template see ``get_output_filename`` and
    ``output`` methods for more information."""

    @property
    def push_urls(self):
        """Remote locations urls where to push content. See :data:`CARRIER_PIGEON_PUSH_URLS`"""
        try:
            return settings.CARRIER_PIGEON_PUSH_URLS[self.name]
        except (AttributeError, KeyError):
            logger.warning(u'No push url setted for rule "%s"' % self.name)
            return []

    @property
    def validators(self):
        """A list a function that takes the content the content of the file
        that will be pushed."""
        return list()

    @abstractmethod
    def filter_by_instance_type(self, instance):
        """**Abstract Method**. It's recommanded to filter instances by type
        in this method."""
        pass

    @abstractmethod
    def filter_by_updates(self, instance):
        """**Abstract Method**. It's recommanded to filter instances by updates
        in this method. This method is called only if it's an update."""
        pass

    @abstractmethod
    def filter_by_state(self, instance):
        """**Abstract Method**. It's recommaned to filter instances by states
        in this method."""
        pass

    @abstractmethod
    def get_directory(self, instance):
        """**Abstract Method**. Utility method used to compute path information
        passed to the pusher. It's used in :class:`~commands.pigeon_push.Command`"""
        pass

    def get_extra_context(self, instance):
        """Extra variables passed to template see
        :meth:`~DefaultConfiguration.output`"""
        return dict()

    def get_output_filename(self, instance):
        """Returns a filename used by :class:`~commands.pigeon_push.Command`
        to build ``output_path``"""
        return '%s_%s_%s.xml' % (instance._meta.app_label.lower(),
                                 instance._meta.module_name,
                                 instance.pk)

    def output(self, instance):
        """Builds templates using a default template build dynamically based
        on the instance. The template that this method should be named
        ``carrier_pigeon/{{ instance._meta.app_label.lower() }}_{{ instance._meta.module_nam }}``
        and be in ``carrier_pigeon/{{ rule_name }}/``. Template context is built
        with values returned by :meth:`~DefaultConfiguration.get_extra_context`
        and ``instance`` as ``object``."""
        rule_name = self.name

        # build template file path
        app_label = instance._meta.app_label.lower()
        class_name = instance._meta.module_name
        template_name = '%s_%s.xml' % (app_label, class_name)

        template_path = 'carrier_pigeon/%s/%s' % (rule_name, template_name)

        template = loader.get_template(template_path)

        context = self.get_extra_context(instance)
        context['object'] = instance
        context = Context(context)
        output = template.render(context)
        return output.encode("utf-8")

    def post_select(self, instance):
        """Called in :func:`~facility.add_item_to_push` after the instance
        added to the :class:`~models.ItemToPush` queue. It can be used to add
        more object linked to instance to ``ItemToPush`` queue."""
        pass

    @property
    def name(self):
        """default name is the name of the class in lower case"""
        return self.__class__.__name__.lower()

