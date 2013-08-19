import os, sys
import tempfile
import shutil

import popit_entity

import requests

import datetime

import json

from popit_entity.resolve import ResolvePopitName

from unittest import TestCase

class ResolvePopitNameTest(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._in_fixtures = os.path.join(os.path.abspath(popit_entity.__path__[0]), 'fixtures', 'test_inputs')

    @classmethod
    def tearDownClass(cls):
        pass

    def test_resolve(self):

        resolver = ResolvePopitName( 
                popit_url = 'http://sa-test.matthew.popit.dev.mysociety.org/api/v0.1/',
                date = datetime.date(month=10, year=2012, day=1) )

        names_file = os.path.join(self._in_fixtures, 'names.test')
        names_fh = open( names_file, 'r' )
        names = json.load( names_fh )

        failed = False

        actual = []

        for (name, expected_id) in names:
            popit_person = resolver.get_person(name)
            got_id = popit_person.id if popit_person else None
            actual.append( (name, got_id) )
            if got_id != expected_id:
                failed = True
                # but carry on

        if failed:
            out_file = 'names.test'
            out = open(out_file, 'w')
            json.dump( actual, out, indent = 4 )

            self.fail( 'Names resolved not as expected! --  diff %s %s' % (out_file, names_file) )

        else:
            self.assertTrue(True) # as doesn't seem to be a .pass() method?

        print >> sys.stderr, '%d / %d resolved' % (resolver.speakers_matched, resolver.speakers_count)






  
