import sys
import random

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import settings

import tracker.models as models
import tracker.viewutil as viewutil
import tracker.prizeutil as prizeutil
import tracker.prizemail as prizemail
import tracker.commandutil as commandutil

class Command(commandutil.TrackerCommand):
    help = 'Draw a specific prize, or all prizes for an event'
    requires_system_checks = False

    def add_arguments(self, parser):
        eventOrPrize = parser.add_mutually_exclusive_group(required=True)
        eventOrPrize.add_argument('-e', '--event', help='specify an event for which event to draw przes', type=viewutil.get_event)
        eventOrPrize.add_argument('-p', '--prize', help='specify which prize to draw', type=int)
        parser.add_argument('-s', '--seed', help='Specify the random seed to use for the drawing.', default=None, required=False)
        parser.add_argument('-d', '--dry-run', help='Run the command, but do not commit any changes to the database.', action='store_true')

    def draw_prize(self, prize):
        # TODO: add checks that the prize drawing time has passed
        status = True
        self.message('Drawing prize #{0}...'.format(prize.pk))
        while status and not prize.maxed_winners():
            status, data = prizeutil.draw_prize(prize, seed=self.rand.getrandbits(256))
            if not status:
                self.message('Error drawing prize #{0}: {1}'.format(prize.id, data['error']))
            else:
                self.message('Assigned prize #{0} to {1}'.format(prize.id, data['winner']))
            self.message('{0}'.format(data), 3)

    def handle(self, *args, **options):
        super(Command,self).handle(*args, **options)

        hasPrize = options['prize'] != None
        hasEvent = options['event'] != None
        dryRun = options['dry_run']

        prizeSet = None

        if hasPrize:
            prizeId = int(options['prize'])
            prizeSet = models.Prize.objects.filter(pk=prizeId)
            if not prizeSet.exists():
                self.message("No prize with id {0} found.".format(prizeId))
                sys.exit(1)      
            elif prizeSet[0].state != 'ACCEPTED':
                self.message("Prize {0} is not in an accepted state".format(prizeId))
                sys.exit(1)
        elif hasEvent:
            event = viewutil.get_event(options['event'])
            prizeSet = models.Prize.objects.filter(event=event, state='ACCEPTED')

        seed = options['seed']

        if seed:
            self.message("Using supplied seed {0}".format(seed))

        self.rand = random.Random(seed)

        if not prizeSet.exists():
            self.message("No prizes match the given query.")        
        else:
            try:
                with transaction.atomic(): 
                    for prize in prizeSet:
                        self.draw_prize(prize)
                    if dryRun:
                        self.message("Rolling back operations...")
                        raise Exception("Cancelled due to dry run.")
            except:
                self.message("Rollback complete.")

        self.message("Completed.")

