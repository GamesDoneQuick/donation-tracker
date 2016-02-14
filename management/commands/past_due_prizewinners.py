from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.viewutil as viewutil
import tracker.prizeutil as prizeutil
import tracker.commandutil as commandutil

class Command(commandutil.TrackerCommand):
    help = "Manage prize winners which have passed their acceptance deadline"

    def add_arguments(self, parser):
        parser.add_argument('-e', '--event', help='Specify the event to target', type=viewutil.get_event, required=True)
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-l', '--list', help='List all prize winners which have passed expiry', action='store_true')
        group.add_argument('-c', '--close', help='Close all prize winners which have passed expiry (does not re-roll)', action='store_true')
        parser.add_argument('-d', '--dry-run', help='Run the command, but do not commit anything to the database', action='store_true')

    def handle(self, *args, **options):
        super(Command,self).handle(*args, **options)
        event = options['event']
        dryRun = options['dry_run']
        pastDueWinners = prizeutil.get_past_due_prize_winners(event)
        
        if not pastDueWinners.exists():
            self.message("There are no past-due winners.", 2)
        elif options['list']:
            for prizeWinner in pastDueWinners:
                self.message("Winner #{0} (due {1})".format(prizeWinner.id, prizeWinner.acceptdeadline))
        elif options['close']:
            prizeutil.close_past_due_prize_winners(pastDueWinners, verbosity=self.verbosity, dry_run=dryRun)
        else:
            self.message("Invalid option.")
