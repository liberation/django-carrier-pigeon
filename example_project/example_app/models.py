# -*- coding: utf-8 -*-

from django.db import models

from extended_choices import Choices

from carrier_pigeon.models import BasicDirtyFieldsMixin

WORKFLOW_STATE = Choices(
   ('OFFLINE', 10, u'Hors ligne'),
   ('ONLINE', 20, u'En ligne'),
   ('DELETED', 99, u'Supprimé'),
)


class Photo(models.Model):
    """One content illustration."""

    title = models.CharField(blank=True, max_length=512)
    credits = models.CharField(blank=True, max_length=100)
    caption = models.CharField(blank=True, max_length=512)
    original_file = models.FileField(upload_to="photo/%Y/%m/%d", max_length=200)
    
    def __unicode__(self):
        return self.title


class Story(models.Model, BasicDirtyFieldsMixin):
    """One content object of a news site."""

    WORKFLOW_STATE = WORKFLOW_STATE

    title = models.CharField(max_length=512)
    workflow_state = models.PositiveSmallIntegerField(
        choices=WORKFLOW_STATE.CHOICES, 
        default=WORKFLOW_STATE.OFFLINE, 
        db_index=True
    )
    content = models.TextField(blank=True, null=True)
    photo = models.ForeignKey(Photo, blank=True, null=True)
    updating_date = models.DateTimeField()

    def __unicode__(self):
        return self.title
