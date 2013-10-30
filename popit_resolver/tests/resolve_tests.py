import os, sys
import tempfile
import shutil

import popit_resolver

import requests

import datetime

import json

from popit_resolver.resolve import ResolvePopitName

from unittest import TestCase

popit_url = 'http://sa-test.matthew.popit.dev.mysociety.org/api/v0.1/'

class ResolvePopitNameTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._in_fixtures = os.path.join(os.path.relpath(popit_resolver.__path__[0]), 'fixtures', 'test_inputs')

    @classmethod
    def tearDownClass(cls):
        pass

    def test_resolve(self):

        resolver = ResolvePopitName( 
                popit_url = popit_url,
                date = datetime.date(month=10, year=2012, day=1) )

        names_file = os.path.join(self._in_fixtures, 'names.test')
        names_fh = open( names_file, 'r' )
        names = json.load( names_fh )

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

        print >> sys.stderr, '%d / %d resolved' % (resolver.speakers_matched, resolver.speakers_count)
