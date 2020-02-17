import tracker.models as models
import tracker.commandutil as commandutil


class Command(commandutil.TrackerCommand):
    help = 'List all events'

    def add_arguments(self, parser):
        parser.add_argument(
            '-n',
            '--non-locked',
            help='list non-locked events only',
            required=False,
            default=False,
        )

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        event_list = models.Event.objects.all()

        if options['non_locked']:
            event_list.filter(locked=False)

        if event_list.exists():
            for event in event_list:
                self.message(
                    '{0} , id: {1}, short: {2}'.format(
                        event.name, event.id, event.short
                    ),
                    0,
                )
        else:
            self.message('No events.')
