# Generated by Django 5.2 on 2025-05-26 17:45

from django.db import migrations, ProgrammingError

from tracker.util import tqdm_groupby


def _update(dc, donations):
    dc.donation_total = sum(d.amount for d in donations)
    count = len(donations)
    dc.donation_count = count
    dc.donation_max = max(d.amount for d in donations) if donations else 0
    if dc.donation_count:
        dc.donation_avg = dc.donation_total / dc.donation_count
    else:
        raise ProgrammingError(
            'got a donation count of 0 when migrating the cache, please report this as a bug'
        )
    # TODO: trying to order by amount in the queryset does not work, but it's probably ok for a one off like this
    donations = sorted(donations, key=lambda d: d.amount)
    if count % 2 == 0:
        dc.donation_med = (donations[count // 2 - 1].amount + donations[count // 2].amount) / 2
    else:
        dc.donation_med = donations[count // 2].amount
    dc.save()


def fill_currencies(apps, schema_editor):
    DonorCache = apps.get_model('tracker', 'DonorCache')
    DonorCache.objects.filter(event=None, currency=None).delete()
    Donation = apps.get_model('tracker', 'Donation')
    Event = apps.get_model('tracker', 'Event')

    donations = Donation.objects.filter(transactionstate='COMPLETED', testdonation=False).select_related('donor', 'event')

    for k, groups in tqdm_groupby(
        donations.order_by('donor', 'event__paypalcurrency'),
        key=lambda d: (d.donor_id, d.event.paypalcurrency),
        unit='row'
    ):
        donor_id, currency = k
        dc = DonorCache.objects.get_or_create(donor_id=donor_id, event=None, currency=currency)[0]
        _update(dc, list(groups))

    for event_id, groups in tqdm_groupby(donations.order_by('event'), key=lambda d: d.event_id, unit='row'):
        dc = DonorCache.objects.get_or_create(donor=None, event_id=event_id, currency=None)[0]
        _update(dc, list(groups))

    for currency in {e[0] for e in Event.objects.values_list('paypalcurrency')}:
        filtered = donations.filter(event__paypalcurrency=currency)
        if filtered:
            dc = DonorCache.objects.get_or_create(donor=None, event=None, currency=currency)[0]
            _update(dc, filtered)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0069_donor_cache_enhancements'),
    ]

    operations = [
        migrations.RunPython(fill_currencies, noop, elidable=True)
    ]
