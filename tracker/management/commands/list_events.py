import tracker.commandutil as commandutil
import tracker.models as models


class Command(commandutil.TrackerCommand):
    help = 'List all events'

    def add_arguments(self, parser):
        parser.add_argument(
            '-n',
            '--non-locked',
            '--non-archived',
            help='list non-archived events only',
            action='store_true',
            required=False,
            default=False,
        )

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        events = models.Event.objects.all()

        if options['non_locked']:
            events.filter(archived=False)

        if events:
            for event in events:
                self.message(
                    f'{event.name}, id: {event.id}, short: {event.short}',
                    0,
                )
        else:
            self.message('No events.')
