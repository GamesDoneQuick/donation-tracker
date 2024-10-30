from django.conf import settings
from django.core.checks import Error, Warning, register
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.db import OperationalError


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
    def TRACKER_CONTRIBUTORS_URL(self):
        return getattr(
            settings,
            'TRACKER_CONTRIBUTORS_URL',
            'https://github.com/GamesDoneQuick/donation-tracker/graphs/contributors',
        )

    @property
    def TRACKER_REGISTRATION_FROM_EMAIL(self):
        return getattr(
            settings, 'TRACKER_REGISTRATION_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL
        )

    @property
    def TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL(self):
        return getattr(
            settings,
            'TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL',
            self.TRACKER_REGISTRATION_FROM_EMAIL,
        )

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
    if not isinstance(TrackerSettings().TRACKER_HAS_CELERY, bool):
        errors.append(Error('TRACKER_HAS_CELERY should be a bool', id='tracker.E100'))
    if hasattr(settings, 'GIANTBOMB_API_KEY'):
        errors.append(
            Warning(
                'GIANTBOMB_API_KEY is deprecated, use TRACKER_GIANTBOMB_API_KEY instead',
                id='tracker.W101',
            )
        )
    if not isinstance(TrackerSettings().TRACKER_GIANTBOMB_API_KEY, str):
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
    if not isinstance(TrackerSettings().TRACKER_PRIVACY_POLICY_URL, str):
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
    if not isinstance(TrackerSettings().TRACKER_SWEEPSTAKES_URL, str):
        errors.append(
            Error('TRACKER_SWEEPSTAKES_URL should be a string', id='tracker.E103')
        )
    if not isinstance(TrackerSettings().TRACKER_PAGINATION_LIMIT, int):
        errors.append(
            Error('TRACKER_PAGINATION_LIMIT should be an integer', id='tracker.E104')
        )
    if not isinstance(TrackerSettings().TRACKER_LOGO, str):
        errors.append(Error('TRACKER_LOGO should be a string', id='tracker.E105'))
    # TODO: validate logo URL works?
    if not isinstance(TrackerSettings().TRACKER_ENABLE_BROWSABLE_API, bool):
        errors.append(
            Error('TRACKER_ENABLE_BROWSABLE_API should be a bool', id='tracker.E106')
        )
    if not isinstance(TrackerSettings().PAYPAL_TEST, bool):
        errors.append(Error('PAYPAL_TEST should be a bool', id='tracker.E107'))
    if not hasattr(settings, 'PAYPAL_TEST'):
        errors.append(
            Error(
                'PAYPAL_TEST is completely missing, set it to True for development/testing and False for production mode',
                id='tracker.E108',
            )
        )
    if not isinstance(TrackerSettings().TRACKER_CONTRIBUTORS_URL, str):
        errors.append(
            Error('TRACKER_CONTRIBUTORS_URL should be a string', id='tracker.E109')
        )
    if not isinstance(TrackerSettings().TRACKER_REGISTRATION_FROM_EMAIL, str):
        errors.append(
            Error(
                'TRACKER_REGISTRATION_FROM_EMAIL should be a string', id='tracker.E114'
            )
        )
    else:
        try:
            EmailValidator()(TrackerSettings().TRACKER_REGISTRATION_FROM_EMAIL)
        except ValidationError:
            errors.append(
                Error(
                    'TRACKER_REGISTRATION_FROM_EMAIL is not a valid email address',
                    id='tracker.E115',
                )
            )
    if not isinstance(TrackerSettings().TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL, str):
        errors.append(
            Error(
                'TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL should be a string',
                id='tracker.E116',
            )
        )
    else:
        try:
            EmailValidator()(
                TrackerSettings().TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL
            )
        except ValidationError:
            errors.append(
                Error(
                    'TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL is not a valid email address',
                    id='tracker.E117',
                )
            )
    site_id = TrackerSettings().TRACKER_PUBLIC_SITE_ID
    if not (site_id is None or isinstance(site_id, int)):
        errors.append(
            Error('TRACKER_PUBLIC_SITE_ID should be None or an int', id='tracker.E118')
        )
    if isinstance(site_id, int):
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            from django.contrib.sites.models import Site

            try:
                if not Site.objects.filter(id=site_id).exists():
                    errors.append(
                        Error(
                            'Site specified by TRACKER_PUBLIC_SITE_ID does not exist',
                            id='tracker.E118',
                        )
                    )
            except OperationalError as e:
                errors.append(
                    Warning(
                        f'TRACKER_PUBLIC_SITE_ID is set, but had an error retrieving it\nEnsure that Sites is installed and migrated before you apply this setting\n{e}',
                        id='tracker.E118',
                    )
                )
        else:
            errors.append(
                Error(
                    'TRACKER_PUBLIC_SITE_ID is set, but the Sites application is not installed',
                    id='tracker.E118',
                )
            )
    return errors
