import argparse
import json

from tracker.management.auth import initialize_default_groups
import tracker.commandutil as commandutil

def parse_perms(permsFile):
    return json.loads(permsFile.read())
    

class Command(commandutil.TrackerCommand):
    help = "(re-)Initialize the set of default auth groups"
    
    def add_arguments(self, parser):
        parser.add_argument('-c', '--clean', help='Unassign any permissions not explicitly given to the groups by the input if they already exist.', action='store_true')
        parser.add_argument('-f', '--file', help='Input file of permissions in json format.', type=argparse.FileType('r'), required=True)
        parser.add_argument('-b', '--break-on-error', help='Break if an error is encountered', action='store_true')

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        initialize_default_groups(groups=parse_perms(options['file']), set_to_default=options['clean'], break_on_error=options['break_on_error'], verbosity=options['verbosity'])
