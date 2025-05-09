from django.apps import AppConfig


class TrackerAppConfig(AppConfig):
    default_auto_field = 'django.db.models.AutoField'
    name = 'tracker'
    verbose_name = 'Donation Tracker'

    def ready(self):
        from tracker import paypalutil  # noqa
