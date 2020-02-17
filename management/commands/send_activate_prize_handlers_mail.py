from django.contrib.auth import get_user_model

import tracker.viewutil as viewutil
import tracker.commandutil as commandutil
import tracker.prizemail as prizemail

AuthUser = get_user_model()


class Command(commandutil.TrackerCommand):
    help = 'Emails any prize handlers whose accounts are not activated at the moment.'

    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--event',
            help='Specify the event to target',
            type=viewutil.get_event,
            required=True,
        )
        parser.add_argument(
            '-t', '--template', help='Mail template to use', required=True
        )
        parser.add_argument(
            '-d',
            '--dry-run',
            help='Run through the motions, but do not send out any mail.',
            action='store_true',
        )

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        event = options['event']

        inactive_users = prizemail.get_event_inactive_prize_handlers(event)
        dry_run = options['dry_run']
        template = options['template']

        if inactive_users.exists():
            prizemail.automail_inactive_prize_handlers(
                event,
                inactive_users,
                template,
                verbosity=self.verbosity,
                dry_run=dry_run,
            )
        else:
            self.message('No inactive users found for the specified event.')
