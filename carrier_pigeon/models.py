from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from extended_choices import Choices


class BasicDirtyFieldsMixin(object):
    """Mixin class that stores modified attributes in ``_modified_attrs``.
    ``modified_attrs`` is reset after save"""

    def __init__(self, *args, **kwargs):
        super(BasicDirtyFieldsMixin, self).__init__(*args, **kwargs)
        self._modified_attrs = None
        self._reset_modified_attrs()

    def _reset_modified_attrs(self):
        self.__dict__['_modified_attrs'] = []

    def __setattr__(self, name, value):
        if (name != '_modified_attrs' and
            hasattr(self, '_modified_attrs') and
            name not in self._modified_attrs):
            if not hasattr(self, name) or value != getattr(self, name):
                self._modified_attrs.append(name)
        super(BasicDirtyFieldsMixin, self).__setattr__(name, value)

    def save(self, *args, **kwargs):
        super(BasicDirtyFieldsMixin, self).save(*args, **kwargs)
        self._reset_modified_attrs()


class ItemToPush(models.Model):
    """Information about items that should be pushed."""
    STATUS = Choices(('NEW', 10, 'New'),
                     ('IN_PROGRESS', 20, 'In progress'),
                     ('PUSHED', 50, 'Pushed'),
                     # ERRORS SHOULD BE OVER 100
                     ('PUSH_ERROR', 110, 'Push error'),
                     ('OUTPUT_GENERATION_ERROR', 120, 'Could not generate output file'),
                     ('SEND_ERROR', 130, 'Could not send file'),
                     ('FILTER_BY_INSTANCE_TYPE_ERROR', 140, 'Error in select during filter by instance type'),
                     ('FILTER_BY_UPDATES_ERROR', 150, 'Error in select during filter by updates'),
                     ('FILTER_BY_STATE_ERROR', 160, 'Error in select during filter by state'),
                     ('GET_DIRECTORY_ERROR', 170, 'Error in select during get directory'),
                     ('VALIDATION_ERROR', 180, 'Failed validation'))

    rule_name = models.SlugField()

    push_url = models.CharField(max_length=300)

    creation_date = models.DateTimeField(auto_now_add=True)
    last_push_attempts_date = models.DateTimeField(null=True)
    push_attempts = models.PositiveIntegerField(default=0)

    status = models.PositiveIntegerField(choices=STATUS.CHOICES,
                                         default=STATUS.NEW)
    message = models.TextField()

    #item to push
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    def __unicode__(self):
        return '%s %s' % (self.rule_name,
                          self.get_status_display())
