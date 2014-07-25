import os
import urllib

from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from popit_resolver.resolve import SetupEntities
from django.core.management import call_command


class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
        make_option( '--popit-api-url', 
            action='store', 
            help='popit url to use',
            default=settings.POPIT_API_URL),
    )


    def handle(self, *args, **options):
        popit_api_url = options.get('popit_api_url', None)

        se = SetupEntities( popit_api_url )
        se.init_popit_data()

