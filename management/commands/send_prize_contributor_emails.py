from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.viewutil as viewutil
import tracker.prizemail as prizemail

class Command(BaseCommand):
    help = 'Sends emails for all prizes that are accepted/denied'

    def add_arguments(self, parser):
        parser.add_argument('-e', '--event', help='specify which event', required=True)
        parser.add_argument('-t', '--template', help='specify an email template', required=False, default=None)

    def handle(self, *args, **options):
        event = viewutil.get_event(options['event'])
        prizes = prizemail.prizes_with_submission_email_pending(event)
        emailTemplate = options['template'] or event.prizecontributoremailtemplate
        
        if emailTemplate == None:
            print("No default prize accept/deny email template specified on event {0}, cannot send e-mails.".format(event.short))
        else:
            prizemail.automail_prize_contributors(event, prizes, emailTemplate)
