import json

from ajax_select.fields import AutoCompleteSelectField, AutoCompleteSelectMultipleField
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import permission_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path

import tracker.models
from tracker import viewutil
from tracker.admin.util import EventLockedMixin, current_or_next_event_id


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

    runs = (
        tracker.models.SpeedRun.objects.filter(event=event)
        .prefetch_related('runners', 'hosts', 'commentators')
        .exclude(order=None)
    )
    for run in runs:
        # TODO: this is horribly inefficient
        run.interstitials = sorted(
            list(tracker.models.Ad.objects.for_run(run))
            + list(tracker.models.Interview.objects.for_run(run)),
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
