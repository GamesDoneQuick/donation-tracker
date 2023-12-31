from django.test import TestCase, override_settings

from tracker import settings


class TestTrackerSettings(TestCase):
    @override_settings(TRACKER_SWEEPSTAKES_URL=None, TOTAL_NONSENSE='flibbertygibbit')
    def test_defaults(self):
        self.assertEqual(settings.TRACKER_PAGINATION_LIMIT, 500)
        self.assertEqual(settings.TRACKER_HAS_CELERY, False)
        self.assertEqual(settings.TRACKER_GIANTBOMB_API_KEY, '')
        self.assertEqual(settings.TRACKER_LOGO, '')
        self.assertEqual(settings.TRACKER_PRIVACY_POLICY_URL, '')
        self.assertEqual(settings.TRACKER_SWEEPSTAKES_URL, '')
        self.assertEqual(settings.TOTAL_NONSENSE, 'flibbertygibbit')

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
