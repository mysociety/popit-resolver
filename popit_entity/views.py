from django.http import HttpResponse, HttpResponseRedirect
from django.utils import simplejson as json
from django.core.urlresolvers import reverse, reverse_lazy
from django.core import serializers
from django.conf import settings
from django.contrib import messages

import datetime

import logging

logger = logging.getLogger(__name__)

