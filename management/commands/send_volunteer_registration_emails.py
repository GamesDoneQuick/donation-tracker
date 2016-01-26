import argparse

from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.viewutil as viewutil
import tracker.volunteer as volunteer
import tracker.commandutil as commandutil

class Command(commandutil.TrackerCommand):
    help = "Creates and sends registration emails for all event volunteers"
    
    requires_system_checks = False
 
    def add_arguments(self, parser):
        parser.add_argument('-d', '--dry-run', help="Run through the action, but don't send any emails or write anything to the database", action='store_true', default=False)
        parser.add_argument('-s', '--sender', help="Sender e-mail address", required=True)
        parser.add_argument('-t', '--template', help="Email template to use", required=True)
        parser.add_argument('-l', '--volunteers-list', help="CSV file with the volunteer information, must have columns 'name', 'username', 'email', and 'position'", required=True)
        parser.add_argument('-e', '--event', help="The event to use", required=True, type=viewutil.get_event)
 
    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        self.message(str(options), 3)
        self.verbosity = options['verbosity']

        dryRun = options['dry_run']
        template = options['template']
        volunteersFile = options['volunteers_list']
        sender = options['sender']
        event = options['event']
        
        volunteers = volunteer.parse_volunteer_info_file(volunteersFile)
        
        volunteer.send_volunteer_mail(settings.DOMAIN, event, volunteers, template, sender, verbosity=self.verbosity, dry_run=dryRun)

