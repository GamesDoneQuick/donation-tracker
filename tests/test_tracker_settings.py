from typing import Type

from django.core.checks import CheckMessage, Error, Warning
from django.test import TestCase, override_settings

from tracker import settings


class TestTrackerSettings(TestCase):
    @override_settings(
        TRACKER_SWEEPSTAKES_URL=None,
        TOTAL_NONSENSE='flibbertygibbit',
        DEFAULT_FROM_EMAIL='foo@example.com',
    )
    def test_defaults(self):
        self.assertEqual(settings.TRACKER_PAGINATION_LIMIT, 500)
        self.assertEqual(settings.TRACKER_HAS_CELERY, False)
        self.assertEqual(settings.TRACKER_GIANTBOMB_API_KEY, '')
        self.assertEqual(settings.TRACKER_LOGO, '')
        self.assertEqual(settings.TRACKER_PRIVACY_POLICY_URL, '')
        self.assertEqual(settings.TRACKER_SWEEPSTAKES_URL, '')
        self.assertEqual(settings.TOTAL_NONSENSE, 'flibbertygibbit')
        self.assertEqual(settings.TRACKER_REGISTRATION_FROM_EMAIL, 'foo@example.com')
        self.assertEqual(
            settings.TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL, 'foo@example.com'
        )

    @override_settings(
        HAS_CELERY=True,
        GIANTBOMB_API_KEY='deadbeef',
        PRIVACY_POLICY_URL='http://example.com/privacy',
        TRACKER_SWEEPSTAKES_URL=None,
        SWEEPSTAKES_URL='http://example.com/sweepstakes',
    )
    def test_deprecated_settings(self):
        self.assertTrue(settings.TRACKER_HAS_CELERY, msg='HAS_CELERY')
        self.assertEqual(
            settings.TRACKER_GIANTBOMB_API_KEY, 'deadbeef', msg='GIANTBOMB_API_KEY'
        )
        self.assertEqual(
            settings.TRACKER_PRIVACY_POLICY_URL,
            'http://example.com/privacy',
            msg='PRIVACY_POLICY_URL',
        )
        self.assertEqual(
            settings.TRACKER_SWEEPSTAKES_URL,
            'http://example.com/sweepstakes',
            msg='SWEEPSTAKES_URL',
        )

    def test_browsable_api(self):
        with override_settings(DEBUG=False):
            self.assertFalse(
                settings.TRACKER_ENABLE_BROWSABLE_API,
                msg='TRACKER_ENABLE_BROWSABLE_API',
            )

        with override_settings(DEBUG=True):
            self.assertTrue(
                settings.TRACKER_ENABLE_BROWSABLE_API,
                msg='TRACKER_ENABLE_BROWSABLE_API',
            )

    def assert_check(
        self,
        code: str,
        cls: Type[CheckMessage] = Error,
        *,
        include_deployment_checks=False,
        **kwargs,
    ):
        from django.core.checks.registry import registry

        with override_settings(**kwargs):
            errors = registry.run_checks(
                include_deployment_checks=include_deployment_checks
            )
            if code[0] == '-':
                self.assertNotIn(
                    code[1:],
                    [e.id for e in errors if cls is None or isinstance(e, cls)],
                )
            else:
                self.assertIn(
                    code,
                    [e.id for e in errors if cls is None or isinstance(e, cls)],
                    msg=f'Could not find `{code}` in {str(errors)}',
                )

    def test_checks(self):
        from django.contrib.auth.models import User
        from django.contrib.sites.models import Site

        User.objects.create(username='coordinator')

        self.assert_check('tracker.W100', Warning, HAS_CELERY=True)
        self.assert_check('tracker.E100', TRACKER_HAS_CELERY=1)
        self.assert_check('tracker.W101', Warning, GIANTBOMB_API_KEY='deadbeef')
        self.assert_check('tracker.E101', TRACKER_GIANTBOMB_API_KEY=1)
        self.assert_check(
            'tracker.W102', Warning, PRIVACY_POLICY_URL='https://example.com/privacy'
        )
        self.assert_check('tracker.E102', TRACKER_PRIVACY_POLICY_URL=1)
        self.assert_check(
            'tracker.W103', Warning, SWEEPSTAKES_URL='https://example.com/privacy'
        )
        self.assert_check('tracker.E103', TRACKER_SWEEPSTAKES_URL=1)
        self.assert_check('tracker.E104', TRACKER_PAGINATION_LIMIT='foo')
        self.assert_check('tracker.E105', TRACKER_LOGO=1)
        self.assert_check('tracker.E106', TRACKER_ENABLE_BROWSABLE_API=1)
        self.assert_check('tracker.E107', PAYPAL_TEST=1)
        # TODO?: PAYPAL_TEST completely missing
        self.assert_check('tracker.E109', TRACKER_CONTRIBUTORS_URL=1)
        self.assert_check('tracker.E110', TRACKER_PAYPAL_MAX_DONATE_AGE='foo')
        self.assert_check('tracker.E111', TRACKER_PAYPAL_SIGNATURE_PREFIX=1)
        self.assert_check('tracker.E111', TRACKER_PAYPAL_SIGNATURE_PREFIX='itistoolong')
        self.assert_check('tracker.E112', TRACKER_PAYPAL_MAXIMUM_AMOUNT='foo')
        self.assert_check('tracker.E113', TRACKER_REGISTRATION_FROM_EMAIL=1)
        self.assert_check(
            'tracker.E113', TRACKER_REGISTRATION_FROM_EMAIL='not.an.email'
        )
        self.assert_check('tracker.E114', TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL=1)
        self.assert_check(
            'tracker.E114', TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL='not.an.email'
        )
        self.assert_check('tracker.E115', TRACKER_PUBLIC_SITE_ID='foo')
        self.assert_check('tracker.E115', TRACKER_PUBLIC_SITE_ID=500)
        site = Site.objects.create(domain='a.site', name='A Site')
        self.assert_check('-tracker.E115', TRACKER_PUBLIC_SITE_ID=site.id)
        # the other Sites checks are extreme edge cases so we will not test those here
        self.assert_check('tracker.W116', Warning, DOMAIN='example.com')
        self.assert_check(
            'tracker.W117', Warning, TRACKER_DEFAULT_PRIZE_COORDINATOR='unknown'
        )
        self.assert_check(
            '-tracker.W117', Warning, TRACKER_DEFAULT_PRIZE_COORDINATOR='coordinator'
        )
        self.assert_check('tracker.E117', TRACKER_DEFAULT_PRIZE_COORDINATOR=1)
