from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.viewutil as viewutil
import tracker.prizemail as prizemail

class Command(BaseCommand):
    help = 'Sends emails for all won prizes that were accepted by their winners'

    def add_arguments(self, parser):
        parser.add_argument('-e', '--event', help='specify which event', required=True)
        parser.add_argument('-t', '--template', help='specify an email template', required=True)

    def handle(self, *args, **options):
        event = viewutil.get_event(options['event'])
        prizeWinners = prizemail.prizes_with_winner_accept_email_pending(event)
        prizemail.automail_winner_accepted_prize(event, prizeWinners, options['template'])
