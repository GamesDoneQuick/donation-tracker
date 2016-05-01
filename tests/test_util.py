import re

from django.test import TestCase

import tracker.util as util

class TestRandomNumReplace(TestCase):
    
    def testMakeAuthCode(self):
        authLen = 555
        testCreate = util.make_auth_code(length=authLen)
        self.assertEqual(authLen, len(testCreate))
        self.assertTrue(re.match('[0-9A-Za-z]+', testCreate))
    
    def testReplaceNoLimit(self):
        original = 'test'
        replaceLen = 8
        modified = util.random_num_replace(original, replaceLen)
        self.assertEqual(len(original) + replaceLen, len(modified))
        self.assertEqual(original, modified[0:len(original)])
        self.assertTrue(re.match('[0-9A-Za-z]+', modified[len(original):]))
    
    def testReplaceWithLimit(self):
        original = 'testingstuff'
        replaceLen = 4
        totalLen = len(original) + 2
        unreplacedLen = totalLen - replaceLen
        modified = util.random_num_replace(original, replaceLen, max_length=totalLen)
        self.assertEqual(totalLen, len(modified))
        self.assertEqual(original[:unreplacedLen], modified[:unreplacedLen])
        self.assertTrue(re.match('[0-9A-Za-z]+', modified[unreplacedLen:]))
    
    def testReplaceStrictLimit(self):
        original = 'testingstuffmore'
        replaceLen = 6
        unreplacedLen = len(original) - replaceLen
        modified = util.random_num_replace(original, replaceLen, max_length=len(original))
        self.assertEqual(len(original), len(modified))
        self.assertEqual(original[:unreplacedLen], modified[:unreplacedLen])
        self.assertTrue(re.match('[0-9A-Za-z]+', modified[unreplacedLen:]))
     
    def testInvalidReplaceLen(self):
        original = 'short'
        replaceLen = 8
        maxLen = 7
        with self.assertRaises(Exception):
            s = util.random_num_replace(original, replaceLen, max_length=maxLen)
