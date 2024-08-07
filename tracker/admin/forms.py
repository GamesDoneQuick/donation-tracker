import datetime

from ajax_select import make_ajax_field
from django import forms as djforms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from tracker import models

from .util import current_or_next_event_id


class DonationBidForm(djforms.ModelForm):
    bid = make_ajax_field(models.DonationBid, 'bid', 'bidtarget')


class BidForm(djforms.ModelForm):
    speedrun = make_ajax_field(models.Bid, 'speedrun', 'run')
    event = make_ajax_field(
        models.Bid, 'event', 'event', initial=current_or_next_event_id
    )
    biddependency = make_ajax_field(models.Bid, 'biddependency', 'allbids')


class CountryRegionForm(djforms.ModelForm):
    country = make_ajax_field(models.CountryRegion, 'country', 'country')

    class Meta:
        model = models.CountryRegion
        exclude = ('', '')


class DonationForm(djforms.ModelForm):
    donor = make_ajax_field(models.Donation, 'donor', 'donor')
    event = make_ajax_field(
        models.Donation, 'event', 'event', initial=current_or_next_event_id
    )

    class Meta:
        model = models.Donation
        exclude = ('', '')


class DonorForm(djforms.ModelForm):
    addresscountry = make_ajax_field(models.Donor, 'addresscountry', 'country')
    user = make_ajax_field(models.Donor, 'user', 'user')

    class Meta:
        model = models.Donor
        exclude = ('', '')


class MilestoneForm(djforms.ModelForm):
    event = make_ajax_field(
        models.Milestone, 'event', 'event', initial=current_or_next_event_id
    )

    class Meta:
        model = models.Milestone
        exclude = ('',)


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
        models.PostbackURL, 'event', 'event', initial=current_or_next_event_id
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
    event = make_ajax_field(
        models.SpeedRun, 'event', 'event', initial=current_or_next_event_id
    )
    runners = make_ajax_field(models.SpeedRun, 'runners', 'runner')
    hosts = make_ajax_field(models.SpeedRun, 'hosts', 'headset')
    commentators = make_ajax_field(models.SpeedRun, 'commentators', 'headset')

    class Meta:
        model = models.SpeedRun
        exclude = ('', '')


class HeadsetAdminForm(djforms.ModelForm):
    runner = make_ajax_field(models.Headset, 'runner', 'runner')

    class Meta:
        model = models.Headset
        exclude = ('', '')


class StartRunForm(djforms.Form):
    next_anchored_run = djforms.DateTimeField(disabled=True, required=False)
    checkpoint_available = djforms.CharField(disabled=True, required=False)
    run_time = djforms.CharField(help_text='Run time of previous run')
    start_time = djforms.DateTimeField(help_text='Start time of current run')
    run_id = djforms.IntegerField(widget=djforms.HiddenInput())

    class Errors:
        invalid_start_time = _(
            'Entered data would cause previous run to end after current run started'
        )
        anchor_time_drift = _(
            'Entered data does not leave enough drift time, please inform an admin and/or adjust the next anchor first'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if 'run_id' in self.initial:
            self._run = models.SpeedRun.objects.filter(
                pk=self.initial['run_id'], event__locked=False
            ).first()
            if self._run and self._run.order:
                self._prev = models.SpeedRun.objects.filter(
                    event=self._run.event, order__lt=self._run.order
                ).last()
            else:
                self._prev = None
        else:
            self._run = None
            self._prev = None

    def clean(self):
        from tracker.models import fields

        cleaned_data = super().clean()
        if not self._run:
            raise ValidationError('Run either does not exist or is on a locked event')
        if not self._prev:
            raise ValidationError('Run does not have a previous run')
        rt = fields.TimestampField.time_string_to_int(cleaned_data['run_time'])
        endtime = self._prev.starttime + datetime.timedelta(milliseconds=rt)
        if cleaned_data['start_time'] < endtime:
            raise ValidationError(self.Errors.invalid_start_time)
        self._prev.run_time = cleaned_data['run_time']
        if self._run.anchor_time is not None:
            self._run.anchor_time = cleaned_data['start_time']
        self._prev.setup_time = str(cleaned_data['start_time'] - endtime)
        try:
            self._run.clean()
            self._prev.clean()
        except ValidationError:
            raise ValidationError(self.Errors.anchor_time_drift)
        return cleaned_data

    def save(self):
        if self.is_valid():
            if self._run.anchor_time is not None:
                self._run.save()
            self._prev.save()


class TestEmailForm(djforms.Form):
    email = djforms.EmailField(help_text='Send a test email to this address')


class LogAdminForm(djforms.ModelForm):
    event = make_ajax_field(
        models.Log, 'event', 'event', initial=current_or_next_event_id
    )

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
    event = make_ajax_field(
        models.Prize, 'event', 'event', initial=current_or_next_event_id
    )
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


class VideoLinkAdminForm(djforms.ModelForm):
    run = make_ajax_field(models.VideoLink, 'run', 'run')
