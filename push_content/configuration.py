class DefaultConfiguration:

    @property
    def push_urls(self):
        raise NotImplementedError()

    @property
    def validators(self):
        raise NotImplementedError()

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
