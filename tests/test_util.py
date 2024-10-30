import re

from django.test import TestCase, override_settings

from tracker import models, util

from .util import today_noon


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
        self.assertEqual(original, modified[0 : len(original)])
        self.assertTrue(re.match('[0-9A-Za-z]+', modified[len(original) :]))

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
        modified = util.random_num_replace(
            original, replaceLen, max_length=len(original)
        )
        self.assertEqual(len(original), len(modified))
        self.assertEqual(original[:unreplacedLen], modified[:unreplacedLen])
        self.assertTrue(re.match('[0-9A-Za-z]+', modified[unreplacedLen:]))

    def testInvalidReplaceLen(self):
        original = 'short'
        replaceLen = 8
        maxLen = 7
        with self.assertRaises(Exception):
            util.random_num_replace(original, replaceLen, max_length=maxLen)


class TestUtil(TestCase):
    def test_median(self):
        self.assertEqual(util.median(models.Donation.objects.all(), 'amount'), 0)
        event = models.Event.objects.create(datetime=today_noon)
        for i in [2, 3, 5, 8, 13]:
            models.Donation.objects.create(event=event, amount=i)
        self.assertEqual(util.median(models.Donation.objects.all(), 'amount'), 5)
        models.Donation.objects.create(event=event, amount=21)
        self.assertEqual(util.median(models.Donation.objects.all(), 'amount'), 6.5)

    def test_flatten(self):
        self.assertSequenceEqual(
            list(util.flatten(['string', [1, 2, 'also_string', [3, 4, 5]]])),
            ['string', 1, 2, 'also_string', 3, 4, 5],
        )

    def test_flatten_dict_values(self):
        self.assertSetEqual(
            set(
                util.flatten_dict(
                    {
                        'root': {'leaf1': 'foo', 'leaf2': ['bar', 'baz']},
                        'branch': 'quux',
                    }
                )
            ),
            {'foo', 'bar', 'baz', 'quux'},
        )

    def test_build_public_url(self):
        from django.contrib.sites.models import Site

        site1 = Site.objects.create(name='One', domain='//one.com')
        site2 = Site.objects.create(name='Two', domain='https://two.com')
        site3 = Site.objects.create(name='Three', domain='three.com')
        with override_settings(TRACKER_PUBLIC_SITE_ID=site1.id):
            self.assertEqual(util.build_public_url('/foo/bar'), '//one.com/foo/bar')
        with override_settings(TRACKER_PUBLIC_SITE_ID=site2.id):
            self.assertEqual(
                util.build_public_url('/foo/bar'), 'https://two.com/foo/bar'
            )
        with override_settings(TRACKER_PUBLIC_SITE_ID=site3.id):
            self.assertEqual(util.build_public_url('/foo/bar'), '//three.com/foo/bar')
        self.assertEqual(util.build_public_url('/foo/bar'), '/foo/bar')
