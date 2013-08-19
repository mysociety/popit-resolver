from django.conf.urls import patterns, url, include
from django.views.decorators.csrf import csrf_exempt

from speeches.views import *
from tastypie.api import Api

v01_api = Api(api_name='v0.1')
# v01_api.register(SpeakerResource())

urlpatterns = patterns('',
    url(r'^api/', include(v01_api.urls))
)

