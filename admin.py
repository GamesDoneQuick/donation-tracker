from django.contrib import admin
import tracker.viewutil as viewutil;
import tracker.views as views;
import tracker.models
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils.text import Truncator
from django.utils.safestring import mark_safe
from django.contrib.admin import widgets;
from django.contrib.admin.widgets import ManyToManyRawIdWidget
from django.utils.encoding import smart_unicode
from django.utils.html import escape

# http://djangosnippets.org/snippets/2217/
class VerboseManyToManyRawIdWidget(widgets.ManyToManyRawIdWidget):
    def label_for_value(self, value):
      print('values: ' + str(value));
      values = value.split(',')
      str_values = []
      key = self.rel.get_related_field().name
      if self.rel.to in self.admin_site._registry:
        for v in values:
          try:
            obj = self.rel.to._default_manager.using(self.db).get(**{key: v})
            x = smart_unicode(obj)
            change_url = reverse(
                "admin:%s_%s_change" % (obj._meta.app_label, obj._meta.object_name.lower()),
                args=(obj.pk,), current_app=self.admin_site.name)
            str_values += ['<strong><a href="%s">%s</a></strong>' % (change_url, escape(x))]
          except (ValueError, self.rel.to.DoesNotExist):
            str_values += [u'???']
        return u', '.join(str_values);
      else:
        return super(VerboseManyToManyRawIdWidget, self).label_for_value(value);

class VerboseForeignKeyRawIdWidget(widgets.ForeignKeyRawIdWidget):
  def url_parameters(self):
    params = super(VerboseForeignKeyRawIdWidget, self).url_parameters();
    # TODO: have it splice in the 'event' parameter to the navigation url under some nebulous conditions
    return params;
  def label_for_value(self, value):
    key = self.rel.get_related_field().name
    if self.rel.to in self.admin_site._registry:
      try:
        obj = self.rel.to._default_manager.using(self.db).get(**{key: value})
        text = '<strong>%s</strong>' % escape(Truncator(obj).words(14, truncate='...'))
        href = reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.module_name), args=(obj.pk,), current_app=self.admin_site.name)
        return '&nbsp;' + ('<a href=%s>' % href) + text + '</a>';
      except (ValueError, self.rel.to.DoesNotExist):
        return u'???'
    else:
      return super(VerboseForeignKeyRawIdWidget, self).label_for_value(value);

def _formfield_for_dbfield(self, klass, db_field, **kwargs):
  if db_field.name in self.raw_id_fields:
    kwargs.pop("request", None)
    type = db_field.rel.__class__.__name__
    if type == "ManyToOneRel":
      kwargs['widget'] = VerboseForeignKeyRawIdWidget(db_field.rel, self.admin_site)
    elif type == "ManyToManyRel":
      kwargs['widget'] = VerboseManyToManyRawIdWidget(db_field.rel, self.admin_site)
    return db_field.formfield(**kwargs)
  return super(klass, self).formfield_for_dbfield(db_field, **kwargs)
      
class CustomModelAdmin(admin.ModelAdmin):
  def formfield_for_dbfield(self, db_field, **kwargs):
    return _formfield_for_dbfield(self, CustomModelAdmin, db_field, **kwargs);

# I don't think there's any other way around this, since I need the functionality in both of them
class CustomStackedInline(admin.StackedInline):
  def formfield_for_dbfield(self, db_field, **kwargs):
    return _formfield_for_dbfield(self, CustomStackedInline, db_field, **kwargs);
  def edit_link(self, instance):
    if instance.id != None:
      url = reverse('admin:{l}_{m}_change'.format(l=instance._meta.app_label,m=instance._meta.module_name), args=[instance.id]);
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

class ChallengeBidInline(CustomStackedInline):
  model = tracker.models.ChallengeBid;
  raw_id_fields = ('challenge', 'donation');
  extra = 0;
  readonly_fields = ('edit_link',);
  
class ChoiceBidAdmin(CustomModelAdmin):
  list_display = ('option', 'donation', 'amount')
  raw_id_fields = ('option', 'donation');

class ChoiceBidInline(CustomStackedInline):
  model = tracker.models.ChoiceBid;
  raw_id_fields = ('option', 'donation');
  extra = 0;
  readonly_fields = ('edit_link',);
  
class ChoiceOptionInline(CustomStackedInline):
  model = tracker.models.ChoiceOption
  raw_id_fields = ('choice',);
  extra = 0;
  readonly_fields = ('edit_link',);

class ChoiceOptionAdmin(CustomModelAdmin):
  list_display = ('choice', 'name')
  search_fields = ('name', 'description', 'choice__name', 'choice__speedrun__name')
  raw_id_fields = ('choice',);

class ChoiceInline(CustomStackedInline):
  model = tracker.models.Choice;
  raw_id_fields = ('speedrun',);
  extra = 0;
  readonly_fields = ('edit_link',);

class ChoiceAdmin(CustomModelAdmin):
  search_fields = ('name', 'speedrun__name', 'description');
  raw_id_fields = ('speedrun',);
  list_filter = ('speedrun__event', 'state')
  inlines = [ChoiceOptionInline]

class DonationInline(CustomStackedInline):
  model = tracker.models.Donation
  raw_id_fields = ('donor',);
  extra = 0;
  readonly_fields = ('edit_link',);

class DonationAdmin(CustomModelAdmin):
  list_display = ('donor', 'amount', 'timereceived', 'event', 'domain', 'transactionstate', 'bidstate', 'readstate', 'commentstate',)
  search_fields = ('donor__email', 'donor__paypalemail', 'donor__alias', 'donor__firstname', 'donor__lastname', 'amount')
  list_filter = ('event', 'transactionstate', 'readstate', 'commentstate', 'bidstate')
  raw_id_fields = ('donor','event');
  inlines = (ChoiceBidInline,ChallengeBidInline);
  
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
  inlines = [DonationInline];
  
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
  raw_id_fields = ['startrun', 'endrun', 'winner', 'event', 'contributors'];
  extra = 0;
  readonly_fields = ('edit_link',);
  
class PrizeAdmin(CustomModelAdmin):
  list_display = ('name', 'category', 'sortkey', 'bidrange', 'games', 'starttime', 'endtime', 'sumdonations', 'randomdraw', 'pin', 'event', 'winner' )
  list_filter = ('event', 'category')
  fieldsets = [
    (None, { 'fields': ['name', 'description', 'image', 'sortkey', 'event', 'contributors', 'pin'] }),
    ('Drawing Parameters', {
      'classes': ['collapse'],
      'fields': ['minimumbid', 'maximumbid', 'sumdonations', 'randomdraw', 'startrun', 'endrun', 'starttime', 'endtime']
    }),
    ('Draw', {
      'fields': ['draw_link', 'winner', 'emailsent'],
    }),
  ]
  readonly_fields = ('draw_link',);
  search_fields = ('name', 'description', 'provided', 'winner__firstname', 'winner__lastname', 'winner__alias', 'winner__email')
  raw_id_fields = ['startrun', 'endrun', 'winner', 'event', 'contributors']
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
  def draw_link(self, instance): #TODO: finish this so it actually draws something
    def generateId(id):
      return 'tracker_prize_draw_link_' + str(id);
    if instance.id != None:
      #prizeUrl = reverse('tracker.views.draw_prize', args=(instance.id,));
      #command = u'var result = $.parseJSON(jQuery.ajax(prizeUrl));';
      #command += u' if('error' in myObj) { 
      link = u'<input type="button" value="Draw Prize Not Working Yet" onClick="window.location.reload()">'
      message = u'<span id="' + generateId(instance.id) + '" />';
      return mark_safe(u'<div>' + link + '&nbsp;' + message + '</div>');
    else:
      return mark_safe(u'Not Saved Yet');

class SpeedRunAdmin(CustomModelAdmin):
  search_fields = ['name', 'description', 'runners_lastname', 'runners_firstname', 'runners_alias']  
  list_filter = ['event']
  inlines = [ChoiceInline, ChallengeInline,PrizeInline]
  fieldsets = [(None, { 'fields': ('name', 'description', 'sortkey', 'event', 'starttime', 'endtime', 'runners') }),];
  raw_id_fields = ('event', 'runners');
  
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
