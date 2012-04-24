import shutil

import os.path

from django.template import Context
from django.template import loader


class BaseOutputMaker(object):

    def __init__(self, configuration, instance):
        self.configuration = configuration
        self.instance = instance

    def output(self):
        raise NotImplementedError("Must be implemented.")

    @property
    def validators(self):
        """ A list of functions that validate the contents of the file
        that will be pushed. """
        return list()

    def get_output_filename(self, instance):
        """ Return the filename used to dump the object data. """
        return self.final_file_name

    @property
    def final_file_name(self):
        raise NotImplementedError("Must be implemented.")

    def get_directory(self):
        """For retrocompatibility."""
        return self.relative_final_directory

    @property
    def relative_final_directory(self):
        """
        Must return the directory where to store the output, relatively to the
        configuration root (remote and local are the same).

        Use an empty string for no directory.
        """
        return ""

    def release(self, output):
        """
        Store in the working dir the final file.
        """
        raise NotImplementedError("Must be implemented.")

    @property
    def local_final_path(self):
        """
        Returns the final file field in the local file system.

        This final path is computed like this:
        / -------------------------- / -------------------------- / ---------- /
        / carrier pigeon working dir / current config working dir / remote dir /
        """
        return os.path.join(
            self.configuration.tmp_directory,
            self.relative_final_path,
        )

    @property
    def local_final_directory(self):
        """
        Returns the final output dir.
        """
        return os.path.join(
            self.configuration.tmp_directory,
            self.relative_final_directory,
        )

    @property
    def relative_final_path(self):
        """
        Must return the path (including file_name) of the output, relatively to
        the configuration root.

        It must not have a slash a the beginning.
        """
        return os.path.join(
            self.relative_final_directory,
            self.final_file_name,
        )


class TemplateOutputMaker(BaseOutputMaker):

    def get_template_name(self):
        """Returns the name of the template used to build the export."""

        app_label = self.instance._meta.app_label.lower()
        class_name = self.instance._meta.module_name
        template_name = '%s_%s.xml' % (app_label, class_name)
        return template_name

    def get_template_path(self):
        """Returns the fully-qualified path to the template to build the export."""

        rule_name = self.configuration.name
        template_name = self.get_template_name()
        return 'carrier_pigeon/%s/%s' % (rule_name, template_name)

    def get_extra_context(self):
        """ If there needs to be some extra context passed to the template,
        just override this method in your own configuration implementation. """

        return dict()

    @property
    def final_file_name(self):
        """ Return the filename used to dump the object data. """

        return '%s_%s_%s.xml' % (self.instance._meta.app_label.lower(),
                                 self.instance._meta.module_name,
                                 self.instance.pk)

    def output(self):
        """ Dump this instance's data into an UTF-8 string. """

        template_path = self.get_template_path()
        template = loader.get_template(template_path)

        context = self.get_extra_context()
        context['object'] = self.instance
        context = Context(context)

        output = template.render(context)
        return output.encode("utf-8")

    def release(self, output):
        """
        Dump the data output in the final file.

        `output` here is the XML content.
        """
        f = open(self.local_final_path, 'w')
        f.write(output)
        f.close()
        return self.local_final_path


class BinaryOutputMaker(BaseOutputMaker):

    def __init__(self, configuration, instance, field_name):
        """
        BinaryOutputMaker needs the field_name aditionnaly to normal parameters.
        """
        super(BinaryOutputMaker, self).__init__(configuration, instance)
        self.file_field = getattr(self.instance, field_name)

    def output(self):
        """ Returns the binary file path. """
        return self.file_field.path

    def get_binary_path(self, instance):
        """ Return the path into which to store the item's related
        binary files. """

        return '%s_%s' % (instance._meta.module_name, instance.pk)

    @property
    def final_file_name(self):
        """ Return the filename used to dump the object data. """

        return '%s_%s' % (self.instance.__class__.__name__, self.instance.pk)

    def release(self, output):
        """
        Copy the original file to the final file.
        
        `output` here is the original file path.
        """
        shutil.copy(output, self.local_final_path)
        return self.local_final_path
