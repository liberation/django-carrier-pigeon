from carrier_pigeon.configuration import DefaultConfiguration


class Testing(DefaultConfiguration):
    def filter_by_instance_type(self, instance):
        return True

    def filter_by_updates(self, instance):
        return True

    def filter_by_state(self, instance):
        return True

    def get_directory(self, instance):
        return 'medias'
