import os, sys
import tempfile
import shutil

import popit_resolver

import requests

import datetime

import json

from popit_resolver.resolve import SetupEntities, ResolvePopitName
from django.core.management import call_command

from unittest import TestCase

popit_url = 'http://za-peoples-assembly.popit.mysociety.org/api/v0.1/'

class ResolvePopitNameTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._in_fixtures = os.path.join(os.path.relpath(popit_resolver.__path__[0]), 'fixtures', 'test_inputs')

        SetupEntities(popit_url).init_popit_data()
        call_command('update_index', verbosity=2)

    @classmethod
    def tearDownClass(cls):
        pass

    def test_aaa(self):
        self.assertTrue(True) # dummy pass, to prevent annoying stacktrace of SQL DDL if first test fails

    def test_resolve(self):

        names_file = os.path.join(self._in_fixtures, 'names.test')
        names_fh = open( names_file, 'r' )
        names = json.load( names_fh )

        resolver = ResolvePopitName( 
                date = datetime.date(month=11, year=2010, day=1) )

        actual = []
        differences = []

        for (name, expected_id) in names:
            popit_person = resolver.get_person(name)
            got_id = popit_person.popit_url.replace( popit_url + 'persons/', '' ) if popit_person else None
            actual.append( (name, got_id) )

            if got_id != expected_id:
                differences.append( (expected_id, got_id) )
                # but carry on

        if len(differences):
            out_file = 'names.test'
            out = open(out_file, 'w')
            json.dump( actual, out, indent = 4 )

            sys.stderr.write( '\n' )

            fixed     = len( filter( lambda (exp,_): exp == None, differences ) )
            regressed = len( filter( lambda (_,got): got == None, differences ) )
            changed   = len(differences) - (fixed + regressed)

            for cat, count in [ ('Fixed', fixed), ('Regressed', regressed), ('Changed', changed) ]:
                if count:
                    sys.stderr.write( '\t%10s:\t%d \n' % (cat, count) )

            sys.stderr.write( '\n' )
            sys.stderr.write( 'Run:   vimdiff %s %s \n' % (out_file, names_file) )
            sys.stderr.write( 'and update latter if required \n' )

            self.fail( 'Names resolved not as expected!')

        else:
            self.assertTrue(True) # as doesn't seem to be a .pass() method?
