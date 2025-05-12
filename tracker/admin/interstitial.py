from django import forms
from django.contrib import admin
from django.http import HttpResponsePermanentRedirect
from django.urls import path, reverse

import tracker.models
from tracker import viewutil
from tracker.admin.filters import InterviewParticipantFilter
from tracker.admin.util import CustomModelAdmin, EventArchivedMixin


@admin.register(tracker.models.Ad)
class InterstitialAdmin(EventArchivedMixin, CustomModelAdmin):
    class Form(forms.ModelForm):
        run = forms.CharField(
            widget=forms.TextInput(attrs={'readonly': 'readonly'}),
            help_text='The run this interstitial will follow',
            required=False,
        )

        def __init__(self, *args, **kwargs):
            super(InterstitialAdmin.Form, self).__init__(*args, **kwargs)
            if self.instance.id:
                self.fields['run'].initial = (
                    self.instance.run and self.instance.run.name
                )

    autocomplete_fields = (
        'event',
        'anchor',
        'tags',
    )
    event_child_fields = ('anchor',)
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

    list_display = ('name', 'tags_', 'event', 'run', 'order', 'suborder')
    list_filter = ('event',)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('tags')

    @admin.display(description='Tags')
    def tags_(self, instance):
        return ', '.join(str(t) for t in instance.tags.all()) or None


@admin.register(tracker.models.Interview)
class InterviewAdmin(InterstitialAdmin):
    exclude = ('clips',)
    autocomplete_fields = InterstitialAdmin.autocomplete_fields + (
        'interviewers',
        'subjects',
    )
    list_filter = InterstitialAdmin.list_filter + (InterviewParticipantFilter,)


def view_full_schedule(request, event=None):
    event = viewutil.get_event(event)

    return HttpResponsePermanentRedirect(
        reverse(
            'admin:tracker_ui',
            kwargs={'extra': 'schedule_editor' + (f'/{event.id}' if event.id else '')},
        )
    )
