import os
import re

from django.db.models import Q

from tracker import commandutil
from tracker.models import Donation, DonorCache, Event
from tracker.util import tqdm_groupby


class Command(commandutil.TrackerCommand):
    help = """Recomputes all DonorCache entries, optionally for certain events. Not particularly efficient. Will use
tqdm for a progress bar if installed and verbosity is not 0, and the environment variable TRACKER_DISABLE_TQDM is set
to any non-blank value."""

    def add_arguments(self, parser):
        parser.add_argument(
            '-e',
            '--events',
            help='Comma separated list of either event PKs, or short names',
        )

    def handle(self, *args, **options):
        super().handle(*args, **options)
        try:
            from tqdm import tqdm
        except ImportError:

            def tqdm(iterable, *_, **__):
                return iterable

        donations = (
            Donation.objects.completed()
            .filter(testdonation=False)
            .select_related('donor', 'event')
        )
        events = Event.objects.all()
        ids = set()

        disable = options['verbosity'] == 0 or os.environ.get(
            'TRACKER_DISABLE_TQDM', ''
        )

        q = Q()
        eq = Q()

        if options['events']:
            for i in options['events'].split(','):
                i = i.strip()
                if re.match(r'\d+', i):
                    q |= Q(event_id=i)
                    eq |= Q(id=i)
                else:
                    q |= Q(event__short__iexact=i)
                    eq |= Q(short__iexact=i)
            donations = donations.filter(q)
            events = events.filter(eq)

        for k, g in tqdm_groupby(
            donations.order_by('event', 'donor'),
            key=lambda d: (d.event, d.donor),
            desc='Event-Donor',
            disable=disable,
            unit='row',
        ):
            event, donor = k
            dc = DonorCache.objects.get_or_create(donor=donor, event=event)[0]
            ids.add(dc.id)
            dc.update()

        for k, g in tqdm_groupby(
            donations.order_by('event__paypalcurrency', 'donor'),
            key=lambda d: (d.event.paypalcurrency, d.donor),
            desc='Currency-Donor',
            disable=disable,
            unit='row',
        ):
            currency, donor = k
            dc = DonorCache.objects.get_or_create(donor=donor, currency=currency)[0]
            ids.add(dc.id)
            dc.update()

        for e in tqdm(events, desc='Event', disable=disable, unit='row'):
            dc = DonorCache.objects.get_or_create(donor=None, event=e)[0]
            ids.add(dc.id)
            dc.update()

        for c in tqdm(
            list(c[0] for c in events.values_list('paypalcurrency')),
            desc='Currency',
            disable=disable,
            unit='row',
        ):
            dc = DonorCache.objects.get_or_create(donor=None, currency=c)[0]
            ids.add(dc.id)
            dc.update()

        for dc in tqdm(
            DonorCache.objects.filter(q).exclude(id__in=ids),
            desc='Stale',
            disable=disable,
            unit='row',
        ):
            dc.update()
