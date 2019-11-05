from django.core.urlresolvers import reverse
from django.http import Http404

from django_ical.views import ICalFeed

from tracker.models.event import SpeedRun
from tracker import viewutil


# Reference the properties used by django-ical:
# https://django-ical.readthedocs.io/en/latest/usage.html#property-reference-and-extensions
class RunsCalendar(ICalFeed):
    """A calendar feed for an event's runs. """

    timezone = 'UTC'
    file_name = 'event.ics'

    def get_object(self, request, event):
        event = viewutil.get_event(event)

        if event.locked:
            raise Http404

        return event

    def title(self, event):
        return '{} Runs'.format(event.name)

    def description(self, event):
        return 'Calendar for runs during {} benefiting {}'.format(
            event.name, event.receivername
        )

    # Exclude runs that haven't been slotted into the schedule yet (ones that
    # have no order set)
    def items(self, event):
        return SpeedRun.objects.filter(event=event, order__isnull=False,).order_by(
            '-starttime'
        )

    def item_title(self, run):
        names = run.runners.values_list('name', flat=True)
        runners = ', '.join(names)
        return '{} ({})'.format(run.name, runners)

    def item_description(self, run):
        return '{}\n\n{}'.format(run.display_name, run.description)

    def item_link(self, run):
        return reverse('tracker:run', args=[run.id])

    def item_class(self, run):
        return 'PUBLIC'

    def item_start_datetime(self, run):
        return run.starttime

    def item_end_datetime(self, run):
        return run.endtime

    def item_status(self, run):
        return 'CONFIRMED'
