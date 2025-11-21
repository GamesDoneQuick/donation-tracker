import datetime
import re
from collections import defaultdict
from typing import Iterable, Optional

import django.core.exceptions
import django.db.utils
import post_office.models
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import validators
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.forms import modelformset_factory
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext as _

import tracker.auth as auth
import tracker.util
import tracker.viewutil as viewutil
import tracker.widgets
from tracker import models, settings
from tracker.validators import nonzero, positive

__all__ = [
    'UsernameForm',
    'DonationSearchForm',
    'BidSearchForm',
    'DonorSearchForm',
    'RunSearchForm',
    'BidSearchForm',
    'PrizeSearchForm',
    'MergeObjectsForm',
    'SendVolunteerEmailsForm',
    'PrizeSubmissionForm',
    'AutomailPrizeContributorsForm',
    'DrawPrizeWinnersForm',
    'AutomailPrizeWinnersForm',
    'RegistrationConfirmationForm',
    'PrizeAcceptanceForm',
    'PrizeShippingFormSet',
]


class UsernameForm(forms.Form):
    username = forms.CharField(
        max_length=255, widget=forms.TextInput(attrs={'class': 'required username'})
    )

    def clean_username(self):
        if 'username' in self.cleaned_data:
            username = self.cleaned_data['username']
            if not re.match(r'^[a-zA-Z0-9_]+$', username):
                raise forms.ValidationError(
                    _('Usernames can only contain letters, numbers, and the underscore')
                )
            if username[:10] == 'openiduser':
                raise forms.ValidationError(
                    _("Username may not start with 'openiduser'")
                )
            if User.objects.filter(username=username).count() > 0:
                raise forms.ValidationError(_('Username already in use'))
            return self.cleaned_data['username']
        return None


class DonorSearchForm(forms.Form):
    q = forms.CharField(required=False, initial=None, max_length=255, label='Search')


class DonationSearchForm(forms.Form):
    feed = forms.ChoiceField(
        required=False,
        initial='recent',
        choices=(('all', 'All'), ('recent', 'Recent')),
        label='Filter',
    )
    q = forms.CharField(required=False, initial=None, max_length=255, label='Search')


class BidSearchForm(forms.Form):
    feed = forms.ChoiceField(
        required=False,
        initial='current',
        choices=(
            ('all', 'All'),
            ('current', 'Current'),
            ('future', 'Future'),
            ('open', 'Open'),
            ('closed', 'Closed'),
        ),
        label='Type',
    )
    q = forms.CharField(required=False, initial=None, max_length=255, label='Search')


class RunSearchForm(forms.Form):
    feed = forms.ChoiceField(
        required=False,
        initial='current',
        choices=(('all', 'All'), ('current', 'Current'), ('future', 'Future')),
        label='Type',
    )
    q = forms.CharField(required=False, initial=None, max_length=255, label='Search')


class PrizeSearchForm(forms.Form):
    feed = forms.ChoiceField(
        required=False,
        initial='upcomming',
        choices=(
            ('all', 'All'),
            ('unwon', 'Not Drawn'),
            ('won', 'Drawn'),
            ('current', 'Current'),
            ('future', 'Future'),
        ),
        label='Type',
    )
    q = forms.CharField(required=False, initial=None, max_length=255, label='Search')


class MergeObjectsForm(forms.Form):
    def __init__(self, model, objects, *args, **kwargs):
        super(MergeObjectsForm, self).__init__(*args, **kwargs)
        self.model = model
        self.choices = []
        for objId in objects:
            choice_name = '#%d: ' % objId + str(self.model.objects.get(id=objId))
            self.choices.append((objId, choice_name))
        self.fields['root'] = forms.ChoiceField(choices=self.choices, required=True)
        self.fields['objects'] = forms.CharField(
            initial=','.join([str(i) for i in objects]), widget=forms.HiddenInput()
        )

    def clean(self):
        root = self.model.objects.get(id=self.cleaned_data['root'])
        objects = []
        for objId in [
            int(x)
            for x in [x for x in self.cleaned_data['objects'].split(',') if bool(x)]
        ]:
            if objId != root.id:
                objects.append(self.model.objects.get(id=objId))
        self.cleaned_data['root'] = root
        self.cleaned_data['objects'] = objects
        return self.cleaned_data


class SendVolunteerEmailsForm(forms.Form):
    template = forms.ModelChoiceField(
        post_office.models.EmailTemplate.objects.all(), empty_label=None
    )
    sender = forms.EmailField(
        initial=lambda: settings.TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL
    )
    volunteers = forms.FileField()


class PrizeSubmissionForm(forms.Form):
    event = forms.ModelChoiceField(
        queryset=models.Event.objects.filter(archived=False),
        required=True,
        widget=forms.HiddenInput(),
    )
    name = forms.CharField(
        max_length=64,
        required=True,
        label='Prize Name',
        help_text='Please use a name that will uniquely identify your prize throughout the event.',
    )
    description = forms.CharField(
        max_length=1024,
        required=True,
        label='Prize Description',
        widget=forms.Textarea,
        help_text='Briefly describe your prize, as you would like it to appear to the public. All descriptions are subject to editing at our discretion.',
    )
    maxwinners = forms.IntegerField(
        required=True,
        initial=1,
        widget=tracker.widgets.NumberInput({'min': 1, 'max': 10}),
        label='Number of Copies',
        help_text='If you are submitting multiple copies of the same prize (e.g. multiple copies of the same print), specify how many. Otherwise, leave this at 1.',
    )
    extrainfo = forms.CharField(
        max_length=1024,
        required=False,
        label='Extra/Non-Public Information',
        widget=forms.Textarea,
        help_text='Enter any additional information you feel the staff should know about your prize. This information will not be made public.',
    )
    estimatedvalue = forms.DecimalField(
        decimal_places=2,
        max_digits=20,
        required=True,
        label='Estimated Value',
        validators=[positive, nonzero],
        help_text='Estimate the actual value of the prize. If the prize is handmade, use your best judgement based on time spent creating it. Note that this is not the bid amount.',
    )
    imageurl = forms.URLField(
        max_length=1024,
        label='Prize Image',
        required=True,
        help_text=mark_safe(
            'Enter the URL of an image of the prize. Please see our notes regarding prize images at the bottom of the form. Images are now required for prize submissions.'
        ),
    )
    creatorname = forms.CharField(
        max_length=64,
        required=False,
        label='Prize Creator',
        help_text='Name of the creator of the prize. This is for crediting/promoting the people who created this prize (please fill this in even if you are the creator).',
    )
    creatoremail = forms.EmailField(
        max_length=128,
        label='Prize Creator Email',
        required=False,
        help_text='Enter an e-mail if the creator of this prize accepts commissions and would like to be promoted through our event. Do not enter an e-mail unless they are known to accept commissions, or you have received their explicit consent.',
    )
    creatorwebsite = forms.URLField(
        max_length=128,
        label='Prize Creator Website',
        required=False,
        help_text="Enter the URL of the prize creator's website or online storefront if applicable.",
    )
    agreement = forms.BooleanField(
        label='Agreement',
        help_text=mark_safe(
            """Check if you agree to the following:
  <ul>
    <li>I am expected to ship the prize myself, and will keep a receipt to be reimbursed for the cost of shipping.</li>
    <li>I currently have the prize in my possession, or can guarantee that I can obtain it within one week of the start of the marathon.</li>
    <li>I agree to communicate with the staff in a timely manner as necessary regarding this prize.</li>
    <li>I agree that all contact information is correct has been provided with the consent of the respective parties.</li>
    <li>I agree that if the prize is no longer available, I will contact the staff immediately to withdraw it, and no later than one month of the start date of the marathon.</li>
  </ul>"""
        ),
    )

    def clean_name(self):
        basename = self.cleaned_data['name']
        prizes = models.Prize.objects.filter(name=basename)
        if not prizes.exists():
            return basename
        name = basename
        count = 1
        while prizes.exists():
            count += 1
            name = basename + ' ' + str(count)
            prizes = models.Prize.objects.filter(name=name)
        raise forms.ValidationError('Prize name taken. Suggestion: "{0}"'.format(name))

    def clean_agreement(self):
        value = self.cleaned_data['agreement']
        if not value:
            raise forms.ValidationError(
                'You must agree with this statement to submit a prize.'
            )
        return value

    def clean(self):
        return self.cleaned_data

    def save(self, event, handler=None):
        provider = ''
        if handler and handler.username != handler.email:
            provider = handler.username
        prize = models.Prize.objects.create(
            event=event,
            name=self.cleaned_data['name'],
            description=self.cleaned_data['description'],
            maxwinners=self.cleaned_data['maxwinners'],
            extrainfo=self.cleaned_data['extrainfo'],
            estimatedvalue=self.cleaned_data['estimatedvalue'],
            minimumbid=5,
            image=self.cleaned_data['imageurl'],
            handler=handler,
            provider=provider,
            creator=self.cleaned_data['creatorname'],
            creatoremail=self.cleaned_data['creatoremail'],
            creatorwebsite=self.cleaned_data['creatorwebsite'],
        )
        prize.clean()
        prize.save()
        return prize


class DrawPrizeWinnersForm(forms.Form):
    def __init__(self, prizes, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.choices = []
        for prize in prizes:
            self.choices.append(
                (
                    prize.id,
                    mark_safe(
                        format_html(
                            '<a href="{0}">{1}</a>', viewutil.admin_url(prize), prize
                        )
                    ),
                )
            )
        self.fields['prizes'] = forms.TypedMultipleChoiceField(
            choices=self.choices,
            initial=[prize.id for prize in prizes],
            coerce=lambda x: int(x),
            label='Prizes',
            empty_value=[],
            widget=forms.widgets.CheckboxSelectMultiple,
        )
        self.fields['seed'] = forms.IntegerField(
            required=False,
            label='Random Seed',
            help_text="Completely optional, if you don't know what this is, don't worry about it",
        )

    def clean(self):
        if 'prizes' in self.cleaned_data:
            self.cleaned_data['prizes'] = models.Prize.objects.filter(
                id__in=self.cleaned_data['prizes']
            )
        return self.cleaned_data


class AutomailPrizeBaseForm(forms.Form):
    class Media:
        js = ['prize_mail_template.js']

    from_address = forms.EmailField(
        max_length=256,
        required=True,
        label='From Address',
        help_text='Specify the e-mail you would like to identify as the sender.',
    )
    reply_address = forms.EmailField(
        max_length=256,
        required=False,
        label='Reply Address',
        help_text='If left blank this will be the same as the from address.',
    )
    email_template = forms.ModelChoiceField(
        queryset=post_office.models.EmailTemplate.objects.exclude(
            name__startswith='default_'
        ),
        empty_label='Pick a template...',
        required=True,
        label='Email Template',
        help_text='Select an email template to use.',
    )

    def __init__(
        self,
        event: models.Event,
        template: Optional[post_office.models.EmailTemplate],
        /,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.fields['from_address'].initial = event.default_prize_coordinator_email
        if template:
            self.fields['email_template'].initial = template.id
            self.template_id = template.id
        else:
            self.template_id = 0

    def clean(self):
        if (
            not self.cleaned_data.get('reply_address', '')
            and 'from_address' in self.cleaned_data
        ):
            self.cleaned_data['reply_address'] = self.cleaned_data['from_address']
        return self.cleaned_data


class AutomailPrizeContributorsForm(AutomailPrizeBaseForm):
    prizes = forms.TypedMultipleChoiceField(
        label='Prizes',
        empty_value=[],
        widget=forms.widgets.CheckboxSelectMultiple,
    )

    def __init__(
        self, prizes: Iterable[models.Prize], event: models.Event, /, *args, **kwargs
    ):
        super().__init__(event, event.prizecontributoremailtemplate, *args, **kwargs)
        self.fields['prizes'].choices = [
            (
                prize.id,
                mark_safe(
                    format_html(
                        '<a href="{0}">{1}</a> State: {2} (<a href="mailto:{3}">{3}</a>) <a href="{4}">Preview</a>',
                        viewutil.admin_url(prize),
                        prize,
                        prize.get_state_display(),
                        prize.handler.email,
                        reverse(
                            'admin:tracker_preview_prize_contributor_mail',
                            args=(prize.id, self.template_id),
                        ),
                    )
                ),
            )
            for prize in prizes
            if prize.handler_id
        ]
        self.fields['prizes'].initial = [prize.id for prize in prizes]

    def clean(self):
        super().clean()
        if 'prizes' in self.cleaned_data:
            self.cleaned_data['prizes'] = models.Prize.objects.filter(
                id__in=self.cleaned_data['prizes']
            )
        return self.cleaned_data


class AutomailPrizeClaimBaseForm(AutomailPrizeBaseForm):
    claims = forms.TypedMultipleChoiceField(
        coerce=lambda x: int(x),
        label='Prize Claims',
        empty_value=[],
        widget=forms.widgets.CheckboxSelectMultiple,
    )

    def __init__(
        self,
        event: models.Event,
        template: Optional[post_office.models.EmailTemplate],
        claims: Iterable[models.PrizeClaim],
        viewname: str,
        /,
        *args,
        **kwargs,
    ):
        super().__init__(event, template, *args, **kwargs)
        self.fields['claims'].choices = [
            (
                claim.id,
                mark_safe(
                    format_html(
                        '<a href="{0}">{1}</a>: <a href="{2}">{3}</a> <a href="{4}">Preview</a>',
                        viewutil.admin_url(claim.prize),
                        claim.prize,
                        viewutil.admin_url(claim.winner),
                        claim.winner,
                        reverse(
                            viewname,
                            args=(claim.id, self.template_id),
                        ),
                    )
                ),
            )
            for claim in claims
        ]
        self.fields['claims'].initial = [claim.id for claim in claims]

    def clean(self):
        super().clean()
        if 'claims' in self.cleaned_data:
            self.cleaned_data['claims'] = models.PrizeClaim.objects.filter(
                id__in=self.cleaned_data.get('claims')
            )
        return self.cleaned_data


def future(date: datetime.date | datetime.datetime):
    if isinstance(date, datetime.datetime):
        date = date.date()
    if date <= timezone.now().date():
        raise ValidationError('date needs to be at least one day in the future')


class AutomailPrizeWinnersForm(AutomailPrizeClaimBaseForm):
    accept_deadline = forms.DateField(validators=[future])

    def __init__(self, claims, event, /, *args, **kwargs):
        super().__init__(
            event,
            event.prizewinneremailtemplate,
            claims,
            'admin:tracker_preview_prize_winner_mail',
            *args,
            **kwargs,
        )
        self.fields['accept_deadline'].initial = timezone.now() + datetime.timedelta(
            weeks=2
        )


class AutomailPrizeAcceptNotifyForm(AutomailPrizeClaimBaseForm):
    def __init__(
        self, claims: Iterable[models.PrizeClaim], event: models.Event, *args, **kwargs
    ):
        super().__init__(
            event,
            event.prizewinneracceptemailtemplate,
            claims,
            'admin:tracker_preview_prize_accept_mail',
            *args,
            **kwargs,
        )


class AutomailPrizeShippedForm(AutomailPrizeClaimBaseForm):
    def __init__(
        self, claims: Iterable[models.PrizeClaim], event: models.Event, *args, **kwargs
    ):
        super().__init__(
            event,
            event.prizeshippedemailtemplate,
            claims,
            'admin:tracker_preview_prize_shipped_mail',
            *args,
            **kwargs,
        )


class RegistrationForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=254, required=True)

    def clean_email(self):
        user = self.get_existing_user()
        if user is not None and user.is_active:
            raise forms.ValidationError(
                'This email is already registered. Please log in, (or reset your password if you forgot it).'
            )
        return self.cleaned_data['email']

    def save(
        self,
        email_template=None,
        token_generator=default_token_generator,
        from_email=None,
        request=None,
        **kwargs,
    ):
        if not email_template:
            email_template = auth.default_registration_template()
        user = self.get_existing_user()
        if user is None:
            email = self.cleaned_data['email']
            username = email
            if len(username) > 30:
                username = email[:30]
            AuthUser = get_user_model()
            tries = 0
            while user is None and tries < 5:
                try:
                    user = AuthUser.objects.create(
                        username=username, email=email, is_active=False
                    )
                except django.db.utils.IntegrityError:
                    tries += 1
                    username = tracker.util.random_num_replace(
                        username, 8, max_length=30
                    )
            if tries >= 5:
                raise forms.ValidationError(
                    'Something horrible happened, please try again'
                )
        return auth.send_registration_mail(
            request,
            user,
            template=email_template,
            sender=from_email,
            token_generator=token_generator,
        )

    def get_existing_user(self):
        AuthUser = get_user_model()
        email = self.cleaned_data['email']
        userSet = AuthUser.objects.filter(email__iexact=email)
        if userSet.count() > 1:
            raise forms.ValidationError(
                f'More than one user has the e-mail {email}. Please contact a server administrator.'
            )
        if userSet.exists():
            return userSet[0]
        else:
            return None


class RegistrationConfirmationForm(forms.Form):
    username = forms.CharField(
        label='User Name',
        max_length=30,
        required=True,
        validators=[
            validators.RegexValidator(
                r'^[\w.@+-]+$',
                'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.',
                'invalid',
            )
        ],
    )
    password = forms.CharField(
        label='Password', widget=forms.PasswordInput(), required=True
    )
    passwordconfirm = forms.CharField(
        label='Confirm Password', widget=forms.PasswordInput(), required=True
    )

    def __init__(
        self, user, token, token_generator=default_token_generator, *args, **kwargs
    ):
        super(RegistrationConfirmationForm, self).__init__(*args, **kwargs)
        self.user = user
        self.token = token
        self.token_generator = token_generator
        if not self.check_token():
            self.fields = {}

    def check_token(self):
        if (
            self.user
            and not self.user.is_active
            and self.token
            and self.token_generator
        ):
            return self.token_generator.check_token(self.user, self.token)
        else:
            return False

    def clean_username(self):
        AuthUser = get_user_model()
        cleaned = AuthUser.normalize_username(self.cleaned_data['username'])
        existing = AuthUser.objects.filter(username__iexact=cleaned).exclude(
            pk=self.user.pk
        )
        if existing.exists():
            raise forms.ValidationError(f'Username {cleaned} is already taken')
        return cleaned

    def clean_password(self):
        if not self.cleaned_data['password']:
            raise forms.ValidationError('Password must not be blank.')
        return self.cleaned_data['password']

    def clean(self):
        if not self.check_token():
            raise forms.ValidationError('User token pair is not valid.')
        if 'password' in self.cleaned_data and 'passwordconfirm' in self.cleaned_data:
            if self.cleaned_data['password'] != self.cleaned_data['passwordconfirm']:
                raise forms.ValidationError('Passwords must match.')
        return self.cleaned_data

    def save(self, commit=True):
        if self.user:
            self.user.username = self.cleaned_data['username']
            self.user.set_password(self.cleaned_data['password'])
            self.user.is_active = True
            if commit is True:
                self.user.save()
        else:
            raise forms.ValidationError('Could not save user.')
        return self.user


class PrizeAcceptanceForm(forms.ModelForm):
    class Meta:
        model = models.PrizeClaim
        fields = []

    def __init__(self, *args, **kwargs):
        super(PrizeAcceptanceForm, self).__init__(*args, **kwargs)
        self.accepted = None

        data = kwargs.get('data', {})

        if 'accept' in data:
            self.accepted = True
        elif 'decline' in data:
            self.accepted = False

        self.fields['count'] = forms.ChoiceField(
            initial=self.instance.pendingcount,
            choices=[(x, x) for x in range(1, self.instance.pendingcount + 1)],
            label='Count',
            help_text='You were selected to win more than one copy of this prize, please select how many you would like to take, or press Deny All if you do not want any of them.',
        )
        if self.instance.pendingcount == 1:
            self.fields['count'].widget = forms.HiddenInput()
        self.fields['total'] = forms.IntegerField(
            initial=self.instance.pendingcount,
            validators=[positive],
            widget=forms.HiddenInput(),
        )
        self.fields['comments'] = forms.CharField(
            max_length=512,
            label='Notes',
            required=False,
            help_text='Please put any additional notes here (such as if you have the option of customizing your prize before it is shipped, or additional delivery information).',
            widget=forms.Textarea(attrs=dict(cols=40, rows=2)),
        )

    def clean_total(self):
        if self.instance.pendingcount != self.cleaned_data['total']:
            raise forms.ValidationError(
                'It seems something changed in your status since you loaded the page. Please review and try again.'
            )
        return self.instance.pendingcount

    def clean_count(self):
        count = int(self.cleaned_data['count'])
        if count > self.instance.pendingcount:
            raise forms.ValidationError('Error, count cannot exceed total')
        return count

    def clean(self):
        errors = defaultdict(list)
        if self.accepted is False:
            self.cleaned_data['count'] = 0
            self.cleaned_data['accept'] = False
        elif self.accepted is None:
            errors[NON_FIELD_ERRORS].append(
                'The way you presented your decision was odd. Please make sure you click one of the two buttons.'
            )
        else:
            if self.cleaned_data.get('count', None) == 0:
                errors['count'].append(
                    'You chose accept with 0 prizes. Perhaps you meant to click the other button? If you do not want any of your prizes, simply click the deny button.'
                )
            else:
                self.cleaned_data['accept'] = True
        if (
            'total' in self.cleaned_data
            and self.instance.pendingcount < self.cleaned_data['total']
        ):
            errors[NON_FIELD_ERRORS].append(
                'There was a data inconsistency, please try again.'
            )
        if errors:
            raise forms.ValidationError(errors)
        return self.cleaned_data

    def save(self, commit=True):
        count = self.cleaned_data['count']
        total = self.cleaned_data['total']
        self.instance.acceptcount += count
        self.instance.declinecount += total - count
        self.instance.pendingcount -= total
        if self.cleaned_data['comments']:
            self.instance.winnernotes += self.cleaned_data['comments'] + '\n'
        if commit is True:
            self.instance.save()
        return self.instance


class AddressForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['addressname'].initial = (
            self.instance.addressname
            or f'{self.instance.firstname} {self.instance.lastname}'.strip()
        )
        self.fields['addressname'].required = True
        self.fields['addresscountry'] = forms.ModelChoiceField(
            queryset=models.Country.objects.all(), required=True
        )
        self.fields['addressstreet'].required = True
        self.fields['addresscity'].required = True
        self.fields['addressstate'].required = True
        self.fields['addresszip'].required = True

    class Meta:
        model = models.Donor
        fields = [
            'addressname',
            'addressstreet',
            'addresscity',
            'addressstate',
            'addresscountry',
            'addresszip',
        ]


class PrizeShippingForm(forms.ModelForm):
    class Meta:
        model = models.PrizeClaim
        fields = [
            'shippingstate',
            'shippingcost',
            'shipping_receipt_url',
            'couriername',
            'trackingnumber',
            'shippingnotes',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['shippingstate'].label = (
            'Shipped yet?' if self.instance.prize.requiresshipping else 'Sent yet?'
        )
        self.fields['shippingcost'].help_text = (
            'Fill in the amount you would like to be reimbursed for (leave blank for zero)'
        )
        self.fields['shipping_receipt_url'].help_text = (
            'Please post a url with an image of the shipping receipt here. If you are uncomfortable uploading this image to a web page, you can send the image to {0} instead'.format(
                self.instance.prize.event.default_prize_coordinator_email
            )
        )
        self.fields['couriername'].help_text = (
            '(e.g. FedEx, DHL, ...) Optional, but nice if you have it'
        )
        self.fields['trackingnumber'].help_text = (
            'Optional, and you must also supply the courier name if you want to provide a tracking number'
        )
        self.fields['shippingnotes'].label = 'Additional Notes'
        self.fields['shippingnotes'].help_text = (
            'Any extra information you would like to relay to the recipient'
        )
        self.fields['shippingnotes'].widget = forms.Textarea(
            attrs=dict(cols=40, rows=2)
        )
        if not self.instance.prize.requiresshipping:
            self.fields['shippingcost'].widget = forms.HiddenInput()
            self.fields['shipping_receipt_url'].widget = forms.HiddenInput()
            self.fields['couriername'].widget = forms.HiddenInput()
            self.fields['trackingnumber'].widget = forms.HiddenInput()


PrizeShippingFormSet = modelformset_factory(models.PrizeClaim, form=PrizeShippingForm)
