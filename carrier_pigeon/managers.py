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
for constant in constants:
    method_name = constant.lower()
    def filter_by_status(self):
        return self.filter(status = getattr(models.ITEM_TO_PUSH_STATUS, constant))
    def query_by_status(self):
        method = getattr(self.get_query_set(), constant)
        return method()
    filter_by_status_method = instancemethod(filter_by_status, None, BaseQuerySet)
    query_by_status_method = instancemethod(filter_by_status, None, BaseManager)
    setattr(BaseQuerySet, method_name, filter_by_status_method)
    setattr(BaseManager, method_name, query_by_status_method)
