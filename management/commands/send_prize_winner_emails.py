from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.viewutil as viewutil
import tracker.prizemail as prizemail
import tracker.commandutil as commandutil

class Command(commandutil.TrackerCommand):
    help = 'Sends emails for all prizes that were won'

    def add_arguments(self, parser):
        parser.add_argument('-e', '--event', help='Specify which event', required=True, type=viewutil.get_event)
        parser.add_argument('-t', '--template', help='Specify an email template. When not given, will default to the template on the event.', default=None)
        parser.add_argument('-d', '--dry-run', help='Run the command, but do not send any e-mails or modify the database', action='store_true') 

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        event = options['event']
        prizeWinners = prizemail.prize_winners_with_email_pending(event)
        emailTemplate = options['template'] or event.prizewinneremailtemplate
        dryRun = options['dry_run']
        
        if emailTemplate == None:
            self.message("No default prize winner email template specified on event {0}, cannot send e-mails.".format(event.short))
        else:
            prizemail.automail_prize_winners(event, prizeWinners, emailTemplate, verbosity=self.verbosity, dry_run=dryRun)

