from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.models as models
import tracker.viewutil as viewutil
import tracker.prizemail as prizemail
import tracker.commandutil as commandutil

class Command(commandutil.TrackerCommand):
    help = 'List all events'

    def add_arguments(self, parser):
        parser.add_argument('-n', '--non-locked', help='list non-locked events only', required=False, default=False)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        eventList = models.Event.objects.all()

        if options['non_locked']:
            eventList.filter(locked=False)
            
        if eventList.exists():
            for event in eventList:
                self.message('{0} , id: {1}, short: {2}'.format(event.name, event.id, event.short), 0)
        else:
            self.message("No events.")
