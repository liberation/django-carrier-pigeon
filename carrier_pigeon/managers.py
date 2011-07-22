from new import instancemethod
from extended_choices import NOT_CONSTANTS

import models

from django.db import models as django_models


# BASE
class BaseQuerySet(django_models.query.QuerySet):
    def failed(self):
        """Chainable filter to retrieve only errors elements."""
        return self.filter(status__gte=100)    


class BaseManager(django_models.Manager):
    use_for_related_fields = True    

    def get_query_set(self):
        """ Use our custom QuerySet. """
        return BaseQuerySet(self.model)
    
    def failed(self):
        return self.get_query_set().failed()
        
constants = [c for c in dir(models.ITEM_TO_PUSH_STATUS) if c not in NOT_CONSTANTS]
for current_constant in constants:
    method_name = current_constant.lower()
    def get_filter_function(constant):
        def filter_by_status(self):
            value = getattr(models.ITEM_TO_PUSH_STATUS, constant)
            return self.filter(status=value)
        return filter_by_status
    filter_by_status = get_filter_function(current_constant)
    filter_by_status_method = instancemethod(filter_by_status, None, BaseQuerySet)
    setattr(BaseQuerySet, method_name, filter_by_status_method)

    def get_query_function(name):
        def query_by_status(self):
            method = getattr(self.get_query_set(), name)
            return method()
        return query_by_status
    query_by_status = get_query_function(method_name)
    query_by_status_method = instancemethod(query_by_status, None, BaseManager)
    setattr(BaseManager, method_name, query_by_status_method)
