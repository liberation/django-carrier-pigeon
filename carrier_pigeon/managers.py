from django.db import models

# BASE
class BaseQuerySet(models.query.QuerySet):
    def failed(self):
        """ Chainable filter to retrieve only errors elements. """
        return self.filter(status__gte=100)
    
    def new(self):
        return self.filter(status=self.model.STATUS.NEW)

class BaseManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        """ Use our custom QuerySet. """
        return BaseQuerySet(self.model)
    
    def failed(self):
        return self.get_query_set().failed()
        
    def new(self):
        return self.get_query_set().new()
