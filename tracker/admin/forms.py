import datetime
from collections import defaultdict

from django import forms as djforms
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.utils.translation import gettext_lazy as _

from tracker import models


class DateTimeLocalInput(djforms.DateTimeInput):
    input_type = 'datetime-local'


class DateTimeLocalField(djforms.DateTimeField):
    # Set DATETIME_INPUT_FORMATS here because, if USE_L10N
    # is True, the locale-dictated format will be applied
    # instead of settings.DATETIME_INPUT_FORMATS.
    # See also:
    # https://developer.mozilla.org/en-US/docs/Web/HTML/Date_and_time_formats

    input_formats = [
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M',
    ]
    widget = DateTimeLocalInput(format='%Y-%m-%dT%H:%M')


class StartRunForm(djforms.Form):
    class Media:
        css = {'all': ('forms/hide_disabled_border.css',)}

    next_anchored_run = djforms.DateTimeField(disabled=True, required=False)
    checkpoint_available = djforms.CharField(disabled=True, required=False)
    run_time = djforms.CharField(help_text='Run time of previous run')
    start_time = DateTimeLocalField(help_text='Start time of current run')
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
                pk=self.initial['run_id'], event__archived=False
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

    def clean_start_time(self):
        t = self.cleaned_data['start_time']
        if t.second >= 30:
            t += datetime.timedelta(minutes=1)
        return t.replace(second=0, microsecond=0)

    def clean(self):
        from tracker.models import fields

        errors = defaultdict(list)

        cleaned_data = super().clean()
        if not self._run:
            errors[NON_FIELD_ERRORS].append(
                'Run either does not exist or is on an archived event'
            )
        elif not self._prev:
            errors[NON_FIELD_ERRORS].append('Run does not have a previous run')
        else:
            rt = fields.TimestampField.coerce_value(cleaned_data['run_time'])
            endtime = self._prev.starttime + datetime.timedelta(milliseconds=rt)
            if cleaned_data['start_time'] < endtime:
                errors['start_time'].append(self.Errors.invalid_start_time)
            else:
                self._prev.run_time = cleaned_data['run_time']
                if self._run.anchor_time is not None:
                    self._run.anchor_time = cleaned_data['start_time']
                self._prev.setup_time = str(cleaned_data['start_time'] - endtime)
                try:
                    self._run.clean()
                    self._prev.clean()
                except ValidationError:
                    errors['start_time'].append(self.Errors.anchor_time_drift)
        if errors:
            raise ValidationError(errors)
        return cleaned_data

    def save(self):
        if self.is_valid():
            if self._run.anchor_time is not None:
                self._run.save()
            self._prev.save()


class TestEmailForm(djforms.Form):
    email = djforms.EmailField(help_text='Send a test email to this address')


class PrizeKeyImportForm(djforms.Form):
    keys = djforms.CharField(widget=djforms.Textarea)

    def clean_keys(self):
        keys = {k.strip() for k in self.cleaned_data['keys'].split('\n') if k.strip()}
        if models.PrizeKey.objects.filter(key__in=keys).exists():
            raise ValidationError('At least one key already exists.')
        return keys
