import calendar
from datetime import datetime
import logging
import os, sys
import re, string

from lxml import etree
from lxml import objectify

from django.db import models
from django.utils import timezone
from django.core.cache import cache

from popit.models import Person, ApiInstance
from popit_resolver.models import EntityName

from haystack.query import SearchQuerySet

logger = logging.getLogger(__name__)

name_rx = re.compile(r'^(\w+) (.*?)( \((\w+)\))?$')
class ResolvePopitName (object):

    def __init__(self,
            date = None,
            date_string = None):

        if date_string:
            date = datetime.strptime('%Y-%m-%d', date_string)
        if not date:
            raise Exception("You must provide a date")

        self.person_cache = {}

    def get_person(self, name):

        person = person_cache.get(name, None)
        if person:
            return person

        persons = ( SearchQuerySet
            .filter(content=name)
            .exclude(
                start_date__gt=self.date,
                end_date__lt  =self.date)
            .models(EntityName))

        person = persons[0]
        raise Exception(person)

        person_cache[name] = person
        

class SetupEntities (object):

    def __init__(self, popit_api_url):
        if not popit_api_url:
            raise Exception("No popit_api_url passed to init_popit_data")
        self.ai, _ = ApiInstance.objects.get_or_create(url=popit_api_url)


    def _get_initials(self, record):

        initials = record.get('initials', None)
        if initials:
            return initials

        given_names = record.get('given_names', None)
        if given_names:
            initials = [a[:1] for a in given_names.split()]
            return ' '.join(initials)

        return ''


    def _get_family_name(self, record):

        family_name = record.get('family_name', None)
        if family_name:
            return family_name

        name = record.get('name', None)
        if not name:
            return None

        given_names = record.get('given_names', None)
        if given_names:
            family_name = trim( name.replace(given_names, '', 1) )
            return family_name

        return name.rsplit(' ', 1)[0]

    def _dates(self, membership):
        def get_date(field):
            value = membership.get(field, None)
            if not value:
                return None
            value = value.replace('-00', '-01')
            try:
                return datetime.strptime(value, '%Y-%m-%d')
            except:
                return None
        return [get_date(field) for field in ['start_date', 'end_date']]

    def init_popit_data(self, delete_existing=False):
        self.ai.fetch_all_from_api()

        def add_url(collection, api_client):
            collection_url = api_client._store['base_url']
            for doc in collection:
                doc['popit_url'] = collection_url + '/' + doc['id']
            return collection

        persons       = self.get_collection('persons', add_url)
        organizations = self.get_collection('organizations')
        memberships   = self.get_collection('memberships')

        for m in memberships.values():
            person = persons[m['person_id']]
            person.setdefault('memberships', [])
            person['memberships'].append(m)

            organization = organizations[m['organization_id']]
            organization.setdefault('memberships', [])
            organization['memberships'].append(m)
            m['organization'] = organization

        for person in persons.values():
            print >> sys.stderr, 'Processing %s' % person.get('name', 'eeek!')

            name = person.get('name', None)
            if not name:
                continue

            popit_person = Person.objects.get( popit_id=person['id'] )

            existing = EntityName.objects.filter( person=popit_person )
            if existing.count():
                if delete_existing:
                    existing.delete()

            def make_name(**kwargs):
                kwargs['person'] = popit_person
                return EntityName.objects.get_or_create(**kwargs)

            initials = self._get_initials(person)
            family_name = self._get_family_name(person)

            make_name(name=name)
            make_name( name=' '.join( [initials, family_name] ) )

            for membership in person['memberships']:
                organization_name = membership['organization']['name']
                (start_date, end_date) = self._dates(membership)
                for field in ['role', 'label']:
                    membership_label = membership.get(field, None)
                    if not membership_label:
                        continue

                    make_name(
                        name=' '.join( [membership_label, organization_name] ),
                        start_date=start_date,
                        end_date=end_date)


    def get_collection(self, collection, fn=None):

        api_client = self.ai.api_client(collection)
        objects = api_client.get()['result']
        if fn:
            objects = fn(objects, api_client)

        objects = dict([ (doc['id'], doc) for doc in objects ])

        return objects

