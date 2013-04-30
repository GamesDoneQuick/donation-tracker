from django.contrib import admin
import tracker.viewutil as viewutil;
import tracker.models
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils.text import Truncator
from django.utils.safestring import mark_safe

from django.contrib.admin import widgets;

class NavigableForeignKeyRawIdWidget(widgets.ForeignKeyRawIdWidget):
  def __init__(self, rel, admin_site, attrs=None, using=None):
    super(NavigableForeignKeyRawIdWidget, self).__init__(rel=rel, admin_site=admin_site, attrs=attrs, using=using);
  def url_parameters(self):
    params = super(NavigableForeignKeyRawIdWidget, self).url_parameters();
    # TODO: have it splice in the 'event' parameter to the navigation url under some nebulous conditions
    return params;
  def label_for_value(self, value):
    key = self.rel.get_related_field().name
    rel_to = self.rel.to
    if rel_to in self.admin_site._registry:
      try:
        obj = self.rel.to._default_manager.using(self.db).get(**{key: value})
        text = '<strong>%s</strong>' % escape(Truncator(obj).words(14, truncate='...'))
        href = reverse('admin:%s_%s_change' % (rel_to._meta.app_label, rel_to._meta.module_name), args=(obj.id,), current_app=self.admin_site.name)
        return '&nbsp;' + ('<a href=%s>' % href) + text + '</a>';
      except (ValueError, self.rel.to.DoesNotExist):
        return ''
    else:
      return super(NavigableForeignKeyRawIdWidget, self).label_for_value(value);

def _create_custom_foreign_key_field(klass, self, db_field, request=None, **kwargs):
  db = kwargs.get('using')
  if db_field.name in self.raw_id_fields:
    kwargs['widget'] = NavigableForeignKeyRawIdWidget(db_field.rel, self.admin_site, using=db)
  else:
    super(klass,self).formfield_for_foreignkey(db_field=db_field, request=request, **kwargs);
  return db_field.formfield(**kwargs)
      
class CustomModelAdmin(admin.ModelAdmin):
  def formfield_for_foreignkey(self, *args, **kwargs):
    return _create_custom_foreign_key_field(CustomModelAdmin, self, *args, **kwargs);

# I don't think there's any other way around this, since I need the functionality in both of them
class CustomStackedInline(admin.StackedInline):
  def formfield_for_foreignkey(self, *args, **kwargs):
    return _create_custom_foreign_key_field(CustomStackedInline, self, *args, **kwargs);
  def edit_link(self, instance):
    if instance.id:
      url = reverse('admin:%s_%s_change' % (instance._meta.app_label,instance._meta.module_name), args=[instance.id]);
      return mark_safe(u'<a href="{u}">Edit</a>'.format(u=url));
    else:
      return mark_safe(u'Not Saved Yet');
  
class ChallengeInline(CustomStackedInline):
  model = tracker.models.Challenge
  raw_id_fields = ('speedrun',);
  extra = 0;
  readonly_fields = ('edit_link',);

class ChallengeAdmin(CustomModelAdmin):
  list_display = ('speedrun', 'name', 'goal', 'description', 'state')
  list_editable = ('name', 'goal', 'state')
  search_fields = ('name', 'speedrun__name', 'description')
  raw_id_fields = ('speedrun',);
  list_filter = ('speedrun__event', 'state')

class ChallengeBidAdmin(CustomModelAdmin):
  list_display = ('challenge', 'donation', 'amount')
  raw_id_fields = ('challenge', 'donation');

class ChoiceBidAdmin(CustomModelAdmin):
  list_display = ('option', 'donation', 'amount')
  raw_id_fields = ('option', 'donation');

class ChoiceOptionInline(CustomStackedInline):
  model = tracker.models.ChoiceOption
  raw_id_fields = ('choice',);
  extra = 0

class ChoiceOptionAdmin(CustomModelAdmin):
  list_display = ('choice', 'name')
  search_fields = ('name', 'description', 'choice__name', 'choice__speedrun__name')
  raw_id_fields = ('choice',);

class ChoiceInline(CustomStackedInline):
  model = tracker.models.Choice;
  raw_id_fields = ('speedrun',);
  extra = 0
  readonly_fields = ('edit_link',);

class ChoiceAdmin(CustomModelAdmin):
  search_fields = ('name', 'speedrun__name', 'description');
  raw_id_fields = ('speedrun',);
  list_filter = ('speedrun__event', 'state')
  inlines = [ChoiceOptionInline]

class DonationInline(CustomStackedInline):
  model = tracker.models.Donation
  raw_id_fields = ('donor',);
  extra = 0
  readonly_fields = ('edit_link',);

class DonationAdmin(CustomModelAdmin):
  list_display = ('donor', 'amount', 'timereceived', 'event', 'domain', 'transactionstate', 'bidstate', 'readstate', 'commentstate',)
  search_fields = ('donor__email', 'donor__paypalemail', 'donor__alias', 'donor__firstname', 'donor__lastname', 'amount')
  list_filter = ('event', 'transactionstate', 'readstate', 'commentstate', 'bidstate')
  raw_id_fields = ('donor',)
  
class RunnerInline(CustomStackedInline):
  model = tracker.models.SpeedRunRunner;
  raw_id_fields = ('runner','run')
  extra = 0;

class PrizeContributorInline(CustomStackedInline):
  model = tracker.models.PrizeContributor;
  raw_id_fields = ('contributor','prize')
  extra = 0;
  
class DonorAdmin(CustomModelAdmin):
  search_fields = ('email', 'paypalemail', 'alias', 'firstname', 'lastname');
  fieldsets = [
    (None, { 'fields': ['email', 'alias', 'firstname', 'lastname', 'visibility'] }),
    ('Donor Info', {
      'classes': ['collapse'],
      'fields': ['paypalemail']
    }),
    ('Address Info', {
      'classes': ['collapse'],
      'fields': ['addressstreet', 'addresscity', 'addressstate', 'addresscountry','addresszip']
    }),
    ('Runner Info', {
      'classes': ['collapse'],
      'fields': ['runneryoutube', 'runnertwitch', 'runnertwitter']
    }),
    ('Prize Contributor Info', {
      'classes': ['collapse'],
      'fields': ['prizecontributoremail', 'prizecontributorwebsite']
    }),
  ];
  inlines = [DonationInline,RunnerInline,PrizeContributorInline];
  
class EventAdmin(CustomModelAdmin):
  search_fields = ('short', 'name');
  fieldsets = [
    (None, { 'fields': ['short', 'name', 'receivername', 'targetamount', 'date'] }),
    ('Paypal', {
      'classes': ['collapse'],
      'fields': ['paypalemail', 'usepaypalsandbox', 'paypalcurrency']
    }),
    ('Google Document', {
      'classes': ['collapse'],
      'fields': ['scheduleid', 'scheduledatetimefield', 'schedulegamefield', 'schedulerunnersfield', 'scheduleestimatefield', 'schedulesetupfield', 'schedulecommentatorsfield', 'schedulecommentsfield']
    }),
  ]

class PrizeInline(CustomStackedInline):
  model = tracker.models.Prize
  fk_name = 'endrun'
  raw_id_fields = ['startrun', 'endrun', 'winner', 'event']
  readonly_fields = ('edit_link',);
  
class PrizeAdmin(CustomModelAdmin):
  list_display = ('name', 'category', 'sortkey', 'bidrange', 'games', 'starttime', 'endtime', 'sumdonations', 'randomdraw', 'pin', 'event', 'winner' )
  list_filter = ('event', 'category')
  search_fields = ('name', 'description', 'provided', 'winner__firstname', 'winner__lastname', 'winner__alias', 'winner__email')
  raw_id_fields = ['startrun', 'endrun', 'winner', 'event']
  inlines = [PrizeContributorInline];
  def bidrange(self, obj):
    s = unicode(obj.minimumbid)
    if obj.minimumbid != obj.maximumbid:
      s += ' <--> ' + unicode(obj.maximumbid)
    return s
  bidrange.short_description = 'Bid Range'
  def games(self, obj):
    s = unicode(obj.startrun.name)
    if obj.startrun != obj.endrun:
      s += ' <--> ' + unicode(obj.endrun.name)
    return s

class SpeedRunAdmin(CustomModelAdmin):
  search_fields = ['name', 'description']  
  list_filter = ['event']
  inlines = [ChoiceInline, ChallengeInline, PrizeInline, RunnerInline]

admin.site.register(tracker.models.Challenge, ChallengeAdmin)
admin.site.register(tracker.models.ChallengeBid, ChallengeBidAdmin)
admin.site.register(tracker.models.Choice, ChoiceAdmin)
admin.site.register(tracker.models.ChoiceBid, ChoiceBidAdmin)
admin.site.register(tracker.models.ChoiceOption, ChoiceOptionAdmin)
admin.site.register(tracker.models.Donation, DonationAdmin)
admin.site.register(tracker.models.Donor, DonorAdmin)
admin.site.register(tracker.models.Event, EventAdmin)
admin.site.register(tracker.models.Prize, PrizeAdmin)
admin.site.register(tracker.models.PrizeCategory)
admin.site.register(tracker.models.SpeedRun, SpeedRunAdmin)
admin.site.register(tracker.models.UserProfile)
