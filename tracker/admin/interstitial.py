import json

from ajax_select.fields import AutoCompleteSelectField
from django import forms
from django.contrib import admin
from django.contrib.auth.decorators import permission_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path

import tracker.models
from tracker import viewutil
from tracker.admin.util import current_or_next_event_id
from tracker.admin.util import EventLockedMixin


@admin.register(tracker.models.Interview, tracker.models.Ad)
class InterstitialAdmin(EventLockedMixin, admin.ModelAdmin):
    class Form(forms.ModelForm):
        class Meta:
            exclude = ('order',)

        event = AutoCompleteSelectField(
            'event', initial=current_or_next_event_id, required=True
        )
        run = AutoCompleteSelectField(
            'run', help_text='The run this interstitial goes after', required=True
        )

        def __init__(self, *args, **kwargs):
            super(InterstitialAdmin.Form, self).__init__(*args, **kwargs)
            if self.instance.id:
                self.fields['run'].initial = self.instance.run and self.instance.run.id

        def clean(self):
            if self.cleaned_data['run']:
                self.cleaned_data['order'] = self.cleaned_data['run'].order
                self.instance.order = self.cleaned_data['run'].order
            return super(InterstitialAdmin.Form, self).clean()

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

    list_display = ('name', 'event', 'run', 'suborder')
    list_filter = ('event',)


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
        run.interstitials = tracker.models.Interstitial.interstitials_for_run(run)
        run.interstitials = list(
            tracker.models.Ad.objects.filter(interstitial_ptr__in=run.interstitials)
        ) + list(
            tracker.models.Interview.objects.filter(
                interstitial_ptr__in=run.interstitials
            )
        )
        run.interstitials = sorted(
            run.interstitials, key=lambda i: (i.order, i.suborder)
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
