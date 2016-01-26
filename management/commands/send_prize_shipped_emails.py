from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.models as models
import tracker.viewutil as viewutil
import tracker.prizemail as prizemail
import tracker.commandutil as commandutil

class Command(commandutil.TrackerCommand):
    help = 'Sends emails for all prizes that have been shipped'

    def add_arguments(self, parser):
        parser.add_argument('-e', '--event', help='Specify the event', type=viewutil.get_event, required=True)
        parser.add_argument('-d', '--dry-run', help='Run the command, but do not send any e-mails or modify the database', action='store_true')
        parser.add_argument('-t', '--template', help='specify an email template', default=None)

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)

        event = options['event']
        prizeWinners = prizemail.prizes_with_shipping_email_pending(event)
        emailTemplate = options['template'] or event.prizeshippedemailtemplate
        dryRun = options['dry_run']
        
        if emailTemplate == None:
            self.message("No default prize shipped email template specified on event {0}, cannot send e-mails.".format(event.short))
        else:
            prizemail.automail_shipping_email_notifications(event, prizeWinners, emailTemplate, verbosity=self.verbosity, dry_run=dryRun)

