import os
import re
from collections import defaultdict
from io import StringIO

from django.test import RequestFactory, TestCase, override_settings

from tracker import models, util

from .util import today_noon


class TestRandomNumReplace(TestCase):
    def testMakeAuthCode(self):
        authLen = 554
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
        with self.assertNumQueries(2):
            # tests both the skipped query and that it actually honors the argument
            self.assertEqual(
                util.median(models.Donation.objects.all(), 'amount', count=3), 3
            )
            self.assertEqual(
                util.median(models.Donation.objects.all(), 'amount', count=4), 4
            )

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
        # TRACKER_PUBLIC_SITE_ID overrides the request host
        request = RequestFactory().get('/bar/foo')
        with override_settings(TRACKER_PUBLIC_SITE_ID=site1.id):
            self.assertEqual(util.build_public_url('/foo/bar'), '//one.com/foo/bar')
            self.assertEqual(
                util.build_public_url('/foo/bar', request), 'http://one.com/foo/bar'
            )
            self.assertEqual(
                util.build_public_url('//two.com/foo/bar'), '//two.com/foo/bar'
            )
        with override_settings(TRACKER_PUBLIC_SITE_ID=site2.id):
            self.assertEqual(
                util.build_public_url('/foo/bar'), 'https://two.com/foo/bar'
            )
            self.assertEqual(
                util.build_public_url('/foo/bar', request), 'https://two.com/foo/bar'
            )
            # keeps the scheme if provided, else uses the one from the site
            self.assertEqual(
                util.build_public_url('http://one.com/foo/bar'),
                'http://one.com/foo/bar',
            )
            self.assertEqual(
                util.build_public_url('//one.com/foo/bar'), 'https://one.com/foo/bar'
            )
        with override_settings(TRACKER_PUBLIC_SITE_ID=site3.id):
            self.assertEqual(util.build_public_url('/foo/bar'), '//three.com/foo/bar')
            self.assertEqual(
                util.build_public_url('/foo/bar', request), 'http://three.com/foo/bar'
            )
            self.assertEqual(
                util.build_public_url('//two.com/foo/bar'), '//two.com/foo/bar'
            )
        # using SITE_ID fallback
        current_site = Site.objects.get_current()
        self.assertEqual(
            util.build_public_url('/foo/bar'), f'//{current_site.domain}/foo/bar'
        )
        with override_settings(SITE_ID=None):
            self.assertEqual(util.build_public_url('/foo/bar'), '/foo/bar')
            self.assertEqual(
                util.build_public_url('/foo/bar', request),
                request.build_absolute_uri('/foo/bar'),
            )


class TestTQDM(TestCase):
    def groups(self, output):
        test = ((1, 0), (1, 1), (2, 0), (2, 1), (2, 2))

        groups = defaultdict(list)

        for k, g in util.tqdm_groupby(
            test, key=lambda i: i[0], file=output, mininterval=0
        ):
            groups[k] += list(g)

        return groups

    def test_tqdm_groupby(self):
        output = StringIO()

        os.environ.pop('TRACKER_DISABLE_TQDM', None)

        groups = self.groups(output)

        self.assertEqual(groups, {1: [(1, 0), (1, 1)], 2: [(2, 0), (2, 1), (2, 2)]})
        self.assertIn('0%', output.getvalue())
        self.assertIn('0/5', output.getvalue())
        self.assertIn('40%', output.getvalue())
        self.assertIn('2/5', output.getvalue())
        self.assertIn('100%', output.getvalue())
        self.assertIn('5/5', output.getvalue())

    def test_tqdm_groupby_without_tqdm(self):
        output = StringIO()

        os.environ['TRACKER_DISABLE_TQDM'] = '1'

        groups = self.groups(output)

        self.assertEqual(groups, {1: [(1, 0), (1, 1)], 2: [(2, 0), (2, 1), (2, 2)]})
        self.assertEqual(output.getvalue(), '')
