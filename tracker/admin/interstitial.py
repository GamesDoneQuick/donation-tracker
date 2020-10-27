import json

import tracker.models
from ajax_select.fields import AutoCompleteSelectField
from django import forms
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.auth.decorators import permission_required
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import path
from tracker import viewutil


@admin.register(tracker.models.Interview, tracker.models.Ad)
class InterstitialAdmin(admin.ModelAdmin):
    class Form(forms.ModelForm):
        class Meta:
            exclude = ('order',)

        run = AutoCompleteSelectField(
            'run', help_text='The run this interstitial goes after', required=True
        )

        def __init__(self, *args, **kwargs):
            super(InterstitialAdmin.Form, self).__init__(*args, **kwargs)
            if self.instance.id:
                self.fields['run'].initial = self.instance.run and self.instance.run.id
            else:
                self.fields['event'].initial = tracker.models.Event.objects.last()

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


@admin.register(tracker.models.HostSlot)
class HostSlotAdmin(admin.ModelAdmin):
    class EventFilter(SimpleListFilter):
        title = 'event'
        parameter_name = 'event'

        def lookups(self, request, model_admin):
            return ((e.id, e.name) for e in tracker.models.Event.objects.all())

        def queryset(self, request, queryset):
            if self.value():
                queryset = queryset.filter(start_run__event=self.value())
            return queryset

    list_filter = [EventFilter]

    class Form(forms.ModelForm):
        start_run = AutoCompleteSelectField('run', required=True)
        end_run = AutoCompleteSelectField('run', required=True)

    form = Form

    def range(self, obj):
        return '%s (%s)' % (obj, obj.start_run.event)

    list_display = ('range', 'name')


@permission_required('tracker.change_interstitial')
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

    runs = tracker.models.SpeedRun.objects.filter(event=event).exclude(order=None)
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
        run.host = tracker.models.HostSlot.host_for_run(run)
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
