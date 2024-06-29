import json

from ajax_select.fields import AutoCompleteSelectField, AutoCompleteSelectMultipleField
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import permission_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path, reverse

import tracker.models
from tracker import viewutil
from tracker.admin.util import EventLockedMixin, current_or_next_event_id
from tracker.compat import pairwise


@admin.register(tracker.models.Ad)
class InterstitialAdmin(EventLockedMixin, admin.ModelAdmin):
    class Form(forms.ModelForm):
        event = AutoCompleteSelectField(
            'event', initial=current_or_next_event_id, required=True
        )
        anchor = AutoCompleteSelectField(
            'run', help_text='The run this interstitial is anchored to', required=False
        )
        run = forms.CharField(
            widget=forms.TextInput(attrs={'readonly': 'readonly'}),
            help_text='The run this interstitial will follow',
            required=False,
        )
        tags = AutoCompleteSelectMultipleField(channel='runtag', required=False)

        def __init__(self, *args, **kwargs):
            super(InterstitialAdmin.Form, self).__init__(*args, **kwargs)
            if self.instance.id:
                self.fields['run'].initial = (
                    self.instance.run and self.instance.run.name
                )

    form = Form

    def name(self, obj):
        return str(obj)

    def run(self, obj):
        return obj.run and obj.run.name

    def get_urls(self):
        return super(InterstitialAdmin, self).get_urls() + [
            path(
                'view_full_schedule',
                self.admin_site.admin_view(view_full_schedule),
                name='view_full_schedule',
            ),
            path(
                'view_full_schedule/<slug:event>',
                self.admin_site.admin_view(view_full_schedule),
                name='view_full_schedule',
            ),
        ]

    list_display = ('name', 'event', 'run', 'order', 'suborder')
    list_filter = ('event',)


@admin.register(tracker.models.Interview)
class InterviewAdmin(InterstitialAdmin):
    exclude = ('clips',)


@permission_required('tracker.view_interstitial')
def view_full_schedule(request, event=None):
    event = viewutil.get_event(event)

    if not event.id:
        return render(
            request,
            'tracker/eventlist.html',
            {
                'events': tracker.models.Event.objects.all(),
                'pattern': 'admin:view_full_schedule',
                'subheading': 'View Full Schedule',
            },
        )

    runs = list(
        tracker.models.SpeedRun.objects.filter(event=event)
        .exclude(order=None)
        .prefetch_related('runners', 'hosts', 'commentators')
    )
    all_interstitials = list(
        tracker.models.Interview.objects.filter(event=event)
    ) + list(tracker.models.Ad.objects.filter(event=event))
    for i in all_interstitials:
        itype = 'ad' if isinstance(i, tracker.models.Ad) else 'interview'
        if request.user.has_perm(f'tracker.view_{itype}'):
            i.admin_url = reverse(f'admin:tracker_{itype}_change', args=(i.id,))
    for c, n in pairwise(runs):
        if request.user.has_perm('tracker.view_speedrun'):
            c.admin_url = reverse('admin:tracker_speedrun_change', args=(c.id,))
        c.interstitials = sorted(
            (i for i in all_interstitials if c.order <= i.order < n.order),
            key=lambda i: (i.order, i.suborder),
        )
    if request.user.has_perm('tracker.view_speedrun'):
        runs[-1].admin_url = reverse(
            'admin:tracker_speedrun_change', args=(runs[-1].id,)
        )
    runs[-1].interstitials = sorted(
        (i for i in all_interstitials if runs[-1].order <= i.order),
        key=lambda i: (i.order, i.suborder),
    )
    if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
        return HttpResponse(
            json.dumps(connection.queries, ensure_ascii=False, indent=1),
            content_type='application/json;charset=utf-8',
        )
    return render(
        request,
        'admin/tracker/view_full_schedule.html',
        {'event': event, 'runs': runs},
    )
