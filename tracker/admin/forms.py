from ajax_select import make_ajax_field
from django import forms as djforms
from django.core.exceptions import ValidationError

from tracker import models

from .util import latest_event_id


class DonationBidForm(djforms.ModelForm):
    bid = make_ajax_field(models.DonationBid, 'bid', 'bidtarget')
    donation = make_ajax_field(models.DonationBid, 'donation', 'donation')


class BidForm(djforms.ModelForm):
    speedrun = make_ajax_field(models.Bid, 'speedrun', 'run')
    event = make_ajax_field(models.Bid, 'event', 'event', initial=latest_event_id)
    biddependency = make_ajax_field(models.Bid, 'biddependency', 'allbids')


class CountryRegionForm(djforms.ModelForm):
    country = make_ajax_field(models.CountryRegion, 'country', 'country')

    class Meta:
        model = models.CountryRegion
        exclude = ('', '')


class DonationForm(djforms.ModelForm):
    donor = make_ajax_field(models.Donation, 'donor', 'donor')
    event = make_ajax_field(models.Donation, 'event', 'event', initial=latest_event_id)

    class Meta:
        model = models.Donation
        exclude = ('', '')


class DonorForm(djforms.ModelForm):
    addresscountry = make_ajax_field(models.Donor, 'addresscountry', 'country')
    user = make_ajax_field(models.Donor, 'user', 'user')

    class Meta:
        model = models.Donor
        exclude = ('', '')


class EventForm(djforms.ModelForm):
    allowed_prize_countries = make_ajax_field(
        models.Event, 'allowed_prize_countries', 'country'
    )
    disallowed_prize_regions = make_ajax_field(
        models.Event, 'disallowed_prize_regions', 'countryregion'
    )
    prizecoordinator = make_ajax_field(models.Event, 'prizecoordinator', 'user')

    class Meta:
        model = models.Event
        exclude = ('', '')


class PostbackURLForm(djforms.ModelForm):
    event = make_ajax_field(
        models.PostbackURL, 'event', 'event', initial=latest_event_id
    )

    class Meta:
        model = models.PostbackURL
        exclude = ('', '')


class RunnerAdminForm(djforms.ModelForm):
    donor = make_ajax_field(models.Runner, 'donor', 'donor')

    class Meta:
        model = models.Runner
        exclude = ('', '')


class SpeedRunAdminForm(djforms.ModelForm):
    event = make_ajax_field(models.SpeedRun, 'event', 'event', initial=latest_event_id)
    runners = make_ajax_field(models.SpeedRun, 'runners', 'runner')
    hosts = make_ajax_field(models.SpeedRun, 'hosts', 'headset')
    commentators = make_ajax_field(models.SpeedRun, 'commentators', 'headset')

    class Meta:
        model = models.SpeedRun
        exclude = ('', '')


class StartRunForm(djforms.Form):
    run_time = djforms.CharField(help_text='Run time of previous run')
    start_time = djforms.DateTimeField(help_text='Start time of current run')


class TestEmailForm(djforms.Form):
    email = djforms.EmailField(help_text='Send a test email to this address')


class LogAdminForm(djforms.ModelForm):
    event = make_ajax_field(models.Log, 'event', 'event', initial=latest_event_id)

    class Meta:
        model = models.Log
        exclude = ('', '')


class PrizeWinnerForm(djforms.ModelForm):
    winner = make_ajax_field(models.PrizeWinner, 'winner', 'donor')
    prize = make_ajax_field(models.PrizeWinner, 'prize', 'prize')

    class Meta:
        model = models.PrizeWinner
        exclude = ('', '')


class DonorPrizeEntryForm(djforms.ModelForm):
    donor = make_ajax_field(models.DonorPrizeEntry, 'donor', 'donor')
    prize = make_ajax_field(models.DonorPrizeEntry, 'prize', 'prize')

    class Meta:
        model = models.DonorPrizeEntry
        exclude = ('', '')


class PrizeForm(djforms.ModelForm):
    event = make_ajax_field(models.Prize, 'event', 'event', initial=latest_event_id)
    startrun = make_ajax_field(models.Prize, 'startrun', 'run')
    endrun = make_ajax_field(models.Prize, 'endrun', 'run')
    handler = make_ajax_field(models.Prize, 'handler', 'user')
    allowed_prize_countries = make_ajax_field(
        models.Prize, 'allowed_prize_countries', 'country'
    )
    disallowed_prize_regions = make_ajax_field(
        models.Prize, 'disallowed_prize_regions', 'countryregion'
    )

    class Meta:
        model = models.Prize
        exclude = ('', '')


class PrizeKeyImportForm(djforms.Form):
    keys = djforms.CharField(widget=djforms.Textarea)

    def clean_keys(self):
        keys = {k.strip() for k in self.cleaned_data['keys'].split('\n') if k.strip()}
        if models.PrizeKey.objects.filter(key__in=keys).exists():
            raise ValidationError('At least one key already exists.')
        return keys
