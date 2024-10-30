from django.conf import settings
from django.core.checks import Error, Warning, register


# noinspection PyPep8Naming
class TrackerSettings(object):
    @property
    def TRACKER_HAS_CELERY(self):
        return getattr(
            settings, 'TRACKER_HAS_CELERY', getattr(settings, 'HAS_CELERY', False)
        )

    @property
    def TRACKER_GIANTBOMB_API_KEY(self):
        return getattr(
            settings,
            'TRACKER_GIANTBOMB_API_KEY',
            getattr(settings, 'GIANTBOMB_API_KEY', ''),
        )

    @property
    def TRACKER_PRIVACY_POLICY_URL(self):
        return getattr(
            settings,
            'TRACKER_PRIVACY_POLICY_URL',
            getattr(settings, 'PRIVACY_POLICY_URL', ''),
        )

    @property
    def TRACKER_SWEEPSTAKES_URL(self):
        # TODO: fix the test suite so that this can be more canonical
        return (
            getattr(settings, 'TRACKER_SWEEPSTAKES_URL', '')
            or getattr(settings, 'SWEEPSTAKES_URL', '')
            or ''
        )

    @property
    def TRACKER_PAGINATION_LIMIT(self):
        return getattr(settings, 'TRACKER_PAGINATION_LIMIT', 500)

    @property
    def TRACKER_LOGO(self):
        return getattr(settings, 'TRACKER_LOGO', '')

    @property
    def TRACKER_ENABLE_BROWSABLE_API(self):
        return getattr(settings, 'TRACKER_ENABLE_BROWSABLE_API', settings.DEBUG)

    @property
    def TRACKER_PUBLIC_SITE_ID(self):
        return getattr(settings, 'TRACKER_PUBLIC_SITE_ID', None)

    # pass everything else through for convenience
    def __getattr__(self, item):
        return getattr(settings, item)


@register
def tracker_settings_checks(app_configs, **kwargs):
    errors = []
    if hasattr(settings, 'HAS_CELERY'):
        errors.append(
            Warning(
                'HAS_CELERY is deprecated, use TRACKER_HAS_CELERY instead',
                id='tracker.W100',
            )
        )
    if type(TrackerSettings().TRACKER_HAS_CELERY) != bool:
        errors.append(Error('TRACKER_HAS_CELERY should be a bool', id='tracker.E100'))
    if hasattr(settings, 'GIANTBOMB_API_KEY'):
        errors.append(
            Warning(
                'GIANTBOMB_API_KEY is deprecated, use TRACKER_GIANTBOMB_API_KEY instead',
                id='tracker.W101',
            )
        )
    if type(TrackerSettings().TRACKER_GIANTBOMB_API_KEY) != str:
        errors.append(
            Error('TRACKER_GIANTBOMB_API_KEY should be a string', id='tracker.E101')
        )
    # TODO: validate Giant Bomb key?
    if hasattr(settings, 'PRIVACY_POLICY_URL'):
        errors.append(
            Warning(
                'PRIVACY_POLICY_URL is deprecated, use TRACKER_PRIVACY_POLICY_URL instead',
                id='tracker.W102',
            )
        )
    if type(TrackerSettings().TRACKER_PRIVACY_POLICY_URL) != str:
        errors.append(
            Error('TRACKER_PRIVACY_POLICY_URL should be a string', id='tracker.E102')
        )
    if hasattr(settings, 'SWEEPSTAKES_URL'):
        errors.append(
            Warning(
                'SWEEPSTAKES_URL is deprecated, use TRACKER_SWEEPSTAKES_URL instead',
                id='tracker.W103',
            )
        )
    if type(TrackerSettings().TRACKER_SWEEPSTAKES_URL) != str:
        errors.append(
            Error('TRACKER_SWEEPSTAKES_URL should be a string', id='tracker.E103')
        )
    if type(TrackerSettings().TRACKER_PAGINATION_LIMIT) != int:
        errors.append(
            Error('TRACKER_PAGINATION_LIMIT should be an integer', id='tracker.E104')
        )
    if type(TrackerSettings().TRACKER_LOGO) != str:
        errors.append(Error('TRACKER_LOGO should be a string', id='tracker.E105'))
    if type(TrackerSettings().TRACKER_ENABLE_BROWSABLE_API) != bool:
        errors.append(
            Error('TRACKER_ENABLE_BROWSABLE_API should be a bool', id='tracker.E106')
        )
    if type(TrackerSettings().PAYPAL_TEST) != bool:
        errors.append(Error('PAYPAL_TEST should be a bool', id='tracker.E107'))
    if not hasattr(settings, 'PAYPAL_TEST'):
        errors.append(
            Error(
                'PAYPAL_TEST is completely missing, set it to True for development/testing and False for production mode',
                id='tracker.E108',
            )
        )
    site_id = TrackerSettings().TRACKER_PUBLIC_SITE_ID
    if not (site_id is None or isinstance(site_id, int)):
        errors.append(
            Error('TRACKER_PUBLIC_SITE_ID should be None or an int', id='tracker.E109')
        )
    if isinstance(site_id, int):
        from django.contrib.sites.models import Site

        if not Site.objects.filter(id=site_id).exists():
            errors.append(
                Error(
                    'Site specified by TRACKER_PUBLIC_SITE_ID does not exist',
                    id='tracker.E110',
                )
            )
    return errors
