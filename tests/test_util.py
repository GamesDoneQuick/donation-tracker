import re

from django.test import TestCase

import tracker.util as util


class TestRandomNumReplace(TestCase):
    def test_make_auth_code(self):
        auth_len = 555
        test_create = util.make_auth_code(length=auth_len)
        self.assertEqual(auth_len, len(test_create))
        self.assertTrue(re.match('[0-9A-Za-z]+', test_create))

    def test_replace_no_limit(self):
        original = 'test'
        replace_len = 8
        modified = util.random_num_replace(original, replace_len)
        self.assertEqual(len(original) + replace_len, len(modified))
        self.assertEqual(original, modified[0 : len(original)])
        self.assertTrue(re.match('[0-9A-Za-z]+', modified[len(original) :]))

    def test_replace_with_limit(self):
        original = 'testingstuff'
        replace_len = 4
        total_len = len(original) + 2
        unreplaced_len = total_len - replace_len
        modified = util.random_num_replace(original, replace_len, max_length=total_len)
        self.assertEqual(total_len, len(modified))
        self.assertEqual(original[:unreplaced_len], modified[:unreplaced_len])
        self.assertTrue(re.match('[0-9A-Za-z]+', modified[unreplaced_len:]))

    def test_replace_strict_limit(self):
        original = 'testingstuffmore'
        replace_len = 6
        unreplaced_len = len(original) - replace_len
        modified = util.random_num_replace(
            original, replace_len, max_length=len(original)
        )
        self.assertEqual(len(original), len(modified))
        self.assertEqual(original[:unreplaced_len], modified[:unreplaced_len])
        self.assertTrue(re.match('[0-9A-Za-z]+', modified[unreplaced_len:]))

    def test_invalid_replace_len(self):
        original = 'short'
        replace_len = 8
        max_len = 7
        with self.assertRaises(Exception):
            util.random_num_replace(original, replace_len, max_length=max_len)
