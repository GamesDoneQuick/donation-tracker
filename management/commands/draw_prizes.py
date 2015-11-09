from django.core.management.base import BaseCommand, CommandError

import settings

import tracker.models as models
import tracker.viewutil as viewutil
import tracker.prizemail as prizemail

class Command(BaseCommand):
    help = 'Draw a specific prize, or all prizes for an event'

    def add_arguments(self, parser):
        parser.add_argument('-e', '--event', help='specify an event for which event to draw przes', required=False)
        parser.add_argument('-p', '--prize', help='specify which prize to draw', required=False)

    def draw_prize(self, prize):
        # TODO: add checks that the prize drawing time has passed
        status = True
        while status and not prize.maxed_winners():
            status, data = viewutil.draw_prize(prize, seed=None)
            if not status:
                print('Error drawing prize #{0} : {1}'.format(prize.id, data['error']))

    def handle(self, *args, **options):
        hasPrize = 'prize' in options
        hasEvent = 'event' in options

        if hasPrize and hasEvent:
            print("Error, cannot specify both a single prize and event.")
        if not hasPrize and not hasEvent:
            print("Error, must specify either a prize or an event.")

        if hasPrize:
            prizeId = int(options['prize'])
            prize = models.Prize(pk=prizeId)
            self.draw_prize(prize)
        elif hasEvent:
            event = viewutil.get_event(options['event'])
            for prize in models.Prize.objects.filter(event=event, state='ACCEPTED'):
                self.draw_prize(prize)
