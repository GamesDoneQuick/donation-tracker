import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class TrackerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'tracker'
    verbose_name = 'Donation Tracker'

    def ready(self):
        try:
            from tracker import paypalutil  # noqa: F401
        except ImportError:
            logger.warning(
                'Could not import PayPal utility module, functionality will be disabled'
            )
