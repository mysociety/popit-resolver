import calendar
from datetime import datetime, date
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
from popit_resolver.search_indexes import EntityNameIndex

from haystack.query import SearchQuerySet

logger = logging.getLogger(__name__)

# TODO these should be added to another table from honorific_prefix in SetupEntities
name_stopwords = re.compile(
    '^(Adv|Chief|Dr|Miss|Mme|Mna|Mnr|Mnu|Moh|Moruti|Moulana|Mr|Mrs|Ms|Njing|Nkk|Nksz|Nom|P|Prince|Prof|Rev|Rre|Umntwana) ')

class ResolvePopitName (object):

    def __init__(self,
            date = None,
            date_string = None):

        if date_string:
            date = datetime.strptime(date_string, '%Y-%m-%d')
        if not date:
            raise Exception("You must provide a date")

        self.date = date
        self.person_cache = {}

    def get_person(self, name):

        person = self.person_cache.get(name, None)
        if person:
            return person

        def _get_person(name):
            if not name:
                return None

            results = ( SearchQuerySet()
                .filter(
                    content=name,
                    start_date__lte=self.date,
                    end_date__gte=self.date
                    )
                .models(EntityName)
                )

            # ElasticSearch may treat the date closeness as more important than the presence of
            # words like Deputy (oops) so we do an additional filter here
            if not re.search('Deputy', name):
                results = [r for r in results if not re.search('Deputy', r.object.name)]

            if len(results):

                result = person = results[0]
                obj = result.object

                # print >> sys.stderr, "SCORE %s" % str( result.score )

                if not obj:
                    print >> sys.stderr, "Unexpected error: are you reusing main Elasticsearch index for tests?"
                    return None

                return obj.person

        (name_sans_paren, paren) = self._get_name_and_paren(name)
        person = (
               _get_person( paren ) # favour this, as it might override
            or _get_person( name ) 
            or _get_person( name_sans_paren ) 
            or _get_person( self._strip_honorific(name) )
            or _get_person( self._strip_honorific(name_sans_paren) )
            )
        if person:
            self.person_cache[name] = person
            return person
        return None

    def _strip_honorific(self, name):
        if not name:
            return None
        (stripped, changed) = re.subn( name_stopwords, '', name )
        if changed:
            return stripped
        return None

    def _get_name_and_paren(self, name):
        s = re.match(r'((?:\w|\s)+) \(((?:\w|\s)+)\)', name)
        if s:
            (pname, paren) = s.groups()
            if len(paren.split()) >= 3:
                # if parens with at least three words
                return (pname, paren)
            else:
                return (pname, None)
        return (None, None)

class SetupEntities (object):

    def __init__(self, popit_api_url):
        if not popit_api_url:
            raise Exception("No popit_api_url passed to SetupEntities()")
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
        return [
            get_date('start_date'),
            get_date('end_date'),
            ]

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
            # print >> sys.stderr, 'Processing %s' % person.get('name', 'eeek!')

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
                kwargs['start_date'] = kwargs.get( 'start_date', None ) or date( year=2000, month=1, day=1 )
                kwargs['end_date']   = kwargs.get( 'end_date',   None ) or date( year=2030, month=1, day=1 )
                return EntityName.objects.get_or_create(**kwargs)

            initials = self._get_initials(person)
            family_name = self._get_family_name(person)
            honorific = person.get('honorific_prefix', '')

            def concat_name(names):
                return ' '.join( [n for n in names if len(n)] )

            full_name          = concat_name( [honorific, name] )
            name_with_initials = concat_name( [honorific, initials, family_name] )

            make_name(name=full_name)
            make_name(name=name_with_initials)

            for membership in person['memberships']:
                organization = membership['organization']
                organization_name = organization['name']
                (start_date, end_date) = self._dates(membership)

                if organization.get('classification', '') == 'party':
                    for n in [full_name, name_with_initials]:
                        name_with_party = '%s (%s)' % (n, organization['name'])
                        make_name(
                            name=name_with_party,
                            start_date=start_date,
                            end_date=end_date)

                for field in ['role', 'label']:
                    membership_label = membership.get(field, None)
                    if not membership_label:
                        continue

                    make_name(
                        name=' '.join( [membership_label, organization_name] ),
                        start_date=start_date,
                        end_date=end_date)

        index = EntityNameIndex()
        # equivalent of manage.py rebuild_index
        index.clear()
        index.update()

    def get_collection(self, collection, fn=None):

        api_client = self.ai.api_client(collection)
        objects = api_client.get()['result']
        if fn:
            objects = fn(objects, api_client)

        objects = dict([ (doc['id'], doc) for doc in objects ])

        return objects

