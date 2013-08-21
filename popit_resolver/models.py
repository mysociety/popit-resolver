import datetime
import logging
import os

from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.files import File

from popit.models import Person

logger = logging.getLogger(__name__)
