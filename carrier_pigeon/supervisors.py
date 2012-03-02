from abc import abstractmethod

from django.conf import settings

class BaseSupervisor(object):
    """
    Parent class to extend for the model supervisors.
    
    This class aims to:
    - filter the instances candidates to the push
    - make the correct output for the instance
    - validate the output
    - possibly instanciate linked ModelSupervisor
    """
    
    def __init__(self, configuration, instance):
        self.configuration = configuration
        self.instance = instance

    @abstractmethod
    def filter_by_instance_type(self, instance):
        pass

    @abstractmethod
    def filter_by_updates(self, instance):
        pass

    @abstractmethod
    def filter_by_state(self, instance):
        pass

    def item_binaries(self, item, depth):
        """ Return the list of binary files linked to this item, by
        listing file-like fields on this item and its related ones.
        Should be implemented in a Linker module. """

        return list()

    def output_binaries(self, item):
        """ Output all `item`'s linked binaries. Return file list.
        Should be implemented in a Linker module. """

        return list()

    def get_output_makers(self):
        raise NotImplementedError("You must implement it.")
    
    def post_select(self, instance):
        pass
    
    def get_related_items(self, item):
        """
        Implement this if you want some related items to be 
        """
        return list()

