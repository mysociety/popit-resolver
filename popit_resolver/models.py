import datetime
import logging
import os

from django.db import models
from django.conf import settings

import popit_resolver

from popit.models import Person

logger = logging.getLogger(__name__)

class EntityName(models.Model):
    name = models.TextField(db_index=True)
    start_date = models.DateField(blank=True, null=True, help_text='What date did this name/position start')
    end_date   = models.DateField(blank=True, null=True, help_text='What date did this name/position start')
    person     = models.ForeignKey(
        Person, 
        blank=True, null=True, 
        on_delete=models.PROTECT, 
        help_text='Associated PopIt object, optional')
