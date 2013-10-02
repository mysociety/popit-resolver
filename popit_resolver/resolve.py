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

logger = logging.getLogger(__name__)
name_rx = re.compile(r'^(\w+) (.*?)( \((\w+)\))?$')

class ResolvePopitName (object):

    def __init__(self,
            popit_url = 'http://sa-test.matthew.popit.dev.mysociety.org/api/v0.1/',
            date = None,
            date_string = None):

        if date:
            date_string = date.strftime('%Y-%m-%d')
        if not date_string:
            raise Error("You must provide a date")

        # TODO get this url from the AN document, or from config/parameter
        self.ai, _ = ApiInstance.objects.get_or_create(url=popit_url)
        self.use_cache = True

        self.person_cache = {}
        self.speakers_count   = 0
        self.speakers_matched = 0
        self.already_spoken = []

        self.init_popit_data( date_string )

    def init_popit_data(self, date_string):
        # TODO this should be in popit-django.  Will try to structure things so that this
        # code can be reused there if possible!

        def add_url(collection, api_client):
            collection_url = api_client._store['base_url']
            for doc in collection:
                doc['popit_url'] = collection_url + '/' + doc['id']
            return collection

        # Stringy comparison is sufficient here
        def date_valid(collection, api_client):
            def _date_valid(doc):
                if doc['start_date']:
                    if start_date > date_string:
                        return False
                if doc['end_date']:
                    if end_date < date_string:
                        return False
                return True

            return filter(_date_valid, collection)

        persons = self.get_collection('persons', add_url)
        organizations = self.get_collection('organizations')
        memberships = self.get_collection('memberships')

        for m in memberships.values():
            person = persons[m['person_id']]
            person.setdefault('memberships', [])
            person['memberships'].append(m)

            organization = organizations[m['organization_id']]
            organization.setdefault('memberships', [])
            organization['memberships'].append(m)

        self.persons = persons
        self.organizations = organizations
        self.memberships = memberships
        self.already_spoken = []

    def get_collection(self, collection, fn=None):

        cache_key = 'ResolvePopitName.get_collection-' + collection

        if self.use_cache:
            cached_value = cache.get(cache_key)
            if cached_value:
                return cached_value

        api_client = self.ai.api_client(collection)
        objects = api_client.get()['result']
        if fn:
            objects = fn(objects, api_client)

        objects = dict([ (doc['id'], doc) for doc in objects ])

        # Cache for one hour
        cache.set(cache_key, objects, 3600)

        return objects

    def get_person(self, name):
        cached = self.person_cache.get(name, None)
        if cached:
            return cached

        if not name:
            raise Exception("No name passed")

        popit_person = None

        self.speakers_count += 1
        popit_person = self.get_popit_person(name)

        if popit_person:
            self.speakers_matched += 1
        else:
            print >> sys.stderr, " - Failed to get user %s" % name

        return popit_person

    def get_popit_person(self, name):

        def _get_popit_person(name):
            person = self.get_best_popit_match(name, self.already_spoken, 0.75)
            if person:
                return person

            person = self.get_best_popit_match(name, self.persons.values(), 0.80)
            if person:
                self.already_spoken.append(person)
                return person

        person = _get_popit_person(name)
        if person:
            ret = Person.update_from_api_results(instance=self.ai, doc=person)
            return ret
            # return Person.update_from_api_results(instance=self.instance, doc="HELLO")

        return None

    def get_best_popit_match(self, name, possible, threshold):
        #TODO: here
        honorific = ''
        party = ''
        match = name_rx.match(name)

        if match:
            honorific, name, _, party = match.groups()

        def _get_initials(record):
            initials = record.get('initials', None)
            if initials:
                return initials
            given_names = record.get('given_names', None)
            if given_names:
                initials = [a[:1] for a in given_names.split()]
                return ' '.join(initials)
            return ''

        def _match(record):
            if name == record.get('name', ''):
                return 1.0

            name_with_initials = '%s %s' % (
                _get_initials(record),
                record.get('family_name', ''))
            if name.lower() == name_with_initials.lower():
                return 0.9


            canon_rx = re.compile(r'((the|of|for|and)\b ?)')
            valid_chars = string.letters + ' '
            def _valid_char(c):
                return c in valid_chars
            def _canonicalize(name):
                return filter(_valid_char, canon_rx.sub('', name.lower()))

            for m in record['memberships']:
                role = m.get('role', '')
                if role:
                    cname = _canonicalize(name)
                    crole = _canonicalize(role)
                    if crole == cname:
                        return 0.9

                    if cname[-7:] == 'speaker':
                        if crole == ('%s national assembly' % cname):
                            return 0.8

            return 0

        for p in possible:
            score = _match(p)
            if score >= threshold:
                return p

        return None

