from django.contrib import admin
import settings;
import tracker.viewutil as viewutil;
import tracker.views as views;
import tracker.forms as forms;
import tracker.models
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils.text import Truncator
from django.utils.safestring import mark_safe
from django.contrib.admin import widgets;
from django.contrib.admin import SimpleListFilter;
from django.contrib.admin.widgets import ManyToManyRawIdWidget
from django.utils.encoding import smart_unicode
from django.utils.html import escape
from django.http import HttpResponseRedirect
from django.contrib import messages;
from django.shortcuts import render;
import django.forms as djforms;
import filters;
from datetime import *;

from ajax_select import make_ajax_field

def reverse_lazy(url):
	return lambda: reverse(url)

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

class DonationListFilter(SimpleListFilter):
  title = 'feed';
  parameter_name = 'feed';
  def lookups(self, request, model_admin):
    return (('recent-5', 'Last 5 Minutes'), ('recent-10','Last 10 Minutes'), ('recent-30','Last 30 Minutes'), ('recent-60','Last Hour'), ('recent-180','Last 3 Hours'),);
  def queryset(self, request, queryset):
    if self.value() is not None:
      return filters.apply_feed_filter(queryset, 'donation', self.value(), user=request.user, noslice=True);
    else:
      return queryset;

class ChallengeListFilter(SimpleListFilter):
  title = 'feed';
  parameter_name = 'feed';
  def lookups(self, request, model_admin):
    return (('current', 'Current'), ('future', 'Future'), ('open','Open'), ('closed', 'Closed'), ('completed', 'Completed'));
  def queryset(self, request, queryset):
    return filters.apply_feed_filter(queryset, 'challenge', self.value(), request.user);

class ChoiceListFilter(SimpleListFilter):
  title = 'feed';
  parameter_name = 'feed';
  def lookups(self, request, model_admin):
    return (('current', 'Current'), ('future', 'Future'), ('open','Open'), ('closed', 'Closed'));
  def queryset(self, request, queryset):
    return filters.apply_feed_filter(queryset, 'choice', self.value(), request.user);

class RunListFilter(SimpleListFilter):
  title = 'feed';
  parameter_name = 'feed';
  def lookups(self, request, model_admin):
    return (('current','Current'), ('future', 'Future'), ('recent-60', 'Last Hour'), ('recent-180', 'Last 3 Hours'), ('recent-300', 'Last 5 Hours'), ('future-60', 'Next Hour'), ('future-180', 'Next 3 Hours'), ('future-300', 'Next 5 Hours'));
  def queryset(self, request, queryset):
    if self.value() is not None:
      return filters.apply_feed_filter(queryset, 'run', self.value(), user=request.user, noslice=True);
    else:
      return queryset;


class PrizeListFilter(SimpleListFilter):
  title = 'feed';
  parameter_name = 'feed';
  def lookups(self, request, model_admin):
    return (('unwon', 'Not Drawn'), ('won', 'Drawn'), ('current', 'Current'), ('upcomming', 'Upcomming'), ('todraw', 'Ready To Draw'));
  def queryset(self, request, queryset):
    return filters.apply_feed_filter(queryset, 'prize', self.value(), request.user);

def bid_open_action(modeladmin, request, queryset):
  bid_set_state_action(modeladmin, request, queryset, 'OPENED');
  return;
bid_open_action.short_description = "Set Bids as OPENED";

def bid_close_action(modeladmin, request, queryset):
  bid_set_state_action(modeladmin, request, queryset, 'CLOSED');
  return;
bid_close_action.short_description = "Set Bids as CLOSED";

def bid_hidden_action(modeladmin, request, queryset):
  bid_set_state_action(modeladmin, request, queryset, 'HIDDEN');
  return;
bid_hidden_action.short_description = "Set Bids as HIDDEN";

def bid_set_state_action(modeladmin, request, queryset, value):
  queryset.update(state=value);
  return;

class ChallengeForm(djforms.ModelForm):
  speedrun = make_ajax_field(tracker.models.Challenge, 'speedrun', 'run')

class ChallengeInline(CustomStackedInline):
  model = tracker.models.Challenge
  extra = 0;
  readonly_fields = ('edit_link',);

class ChallengeAdmin(CustomModelAdmin):
  form = ChallengeForm
  list_display = ('speedrun', 'name', 'goal', 'description', 'state')
  list_editable = ('name', 'goal', 'state')
  search_fields = ('name', 'speedrun__name', 'description')
  list_filter = ('speedrun__event', 'state', ChallengeListFilter)
  actions = [bid_open_action, bid_close_action, bid_hidden_action];

class ChallengeBidForm(djforms.ModelForm):
  challenge = make_ajax_field(tracker.models.ChallengeBid, 'challenge', 'challenge', add_link=reverse_lazy('admin:tracker_challenge_add'))
  donation = make_ajax_field(tracker.models.ChallengeBid, 'donation', 'donation')

class ChallengeBidAdmin(CustomModelAdmin):
  form = ChallengeBidForm
  list_display = ('challenge', 'donation', 'amount')

class ChallengeBidInline(CustomStackedInline):
  form = ChallengeBidForm
  model = tracker.models.ChallengeBid;
  extra = 0;
  max_num=100
  readonly_fields = ('edit_link',);

class ChoiceBidForm(djforms.ModelForm):
  option = make_ajax_field(tracker.models.ChoiceBid, 'option', 'choiceoption', add_link=reverse_lazy('admin:tracker_choiceoption_add'))
  donation = make_ajax_field(tracker.models.ChoiceBid, 'donation', 'donation')

class ChoiceBidAdmin(CustomModelAdmin):
  form = ChoiceBidForm
  list_display = ('option', 'donation', 'amount')

class ChoiceBidInline(CustomStackedInline):
  form = ChoiceBidForm
  model = tracker.models.ChoiceBid;
  raw_id_fields = ('option', 'donation');
  extra = 0;
  readonly_fields = ('edit_link',);

class ChoiceOptionInline(CustomStackedInline):
  model = tracker.models.ChoiceOption
  raw_id_fields = ('choice',);
  extra = 0;
  readonly_fields = ('edit_link',);

class ChoiceOptionForm(djforms.ModelForm):
  choice = make_ajax_field(tracker.models.ChoiceOption, 'choice', 'choice', add_link=reverse_lazy('admin:tracker_choice_add'))

class ChoiceOptionAdmin(CustomModelAdmin):
  form = ChoiceOptionForm
  list_display = ('choice', 'name')
  search_fields = ('name', 'description', 'choice__name', 'choice__speedrun__name')
  list_filter = ('choice__speedrun__event',);

class ChoiceForm(djforms.ModelForm):
  speedrun = make_ajax_field(tracker.models.Choice, 'speedrun', 'run')

class ChoiceInline(CustomStackedInline):
  form = ChoiceForm
  model = tracker.models.Choice;
  extra = 0;
  readonly_fields = ('edit_link',);

class ChoiceAdmin(CustomModelAdmin):
  form = ChoiceForm
  list_display = ('speedrun', 'name', 'description', 'state')
  search_fields = ('name', 'speedrun__name', 'description');
  list_filter = ('speedrun__event', 'state', ChoiceListFilter)
  inlines = [ChoiceOptionInline];
  actions = [bid_open_action, bid_close_action, bid_hidden_action];

class DonationForm(djforms.ModelForm):
  donor = make_ajax_field(tracker.models.Donation, 'donor', 'donor', add_link=reverse_lazy('admin:tracker_donor_add'))

class DonationInline(CustomStackedInline):
  form = DonationForm
  model = tracker.models.Donation
  raw_id_fields = ('donor',);
  extra = 0;
  readonly_fields = ('edit_link',);

def mass_assign_action(self, request, queryset, field, value):
  queryset.update(**{ field: value });
  self.message_user(request, "Updated %s to %s" % (field, value));

class DonationAdmin(CustomModelAdmin):
  form = DonationForm
  list_display = ('donor', 'amount', 'comment', 'timereceived', 'event', 'domain', 'transactionstate', 'bidstate', 'readstate', 'commentstate',)
  list_editable = ('transactionstate', 'bidstate', 'readstate', 'commentstate');
  search_fields = ('donor__email', 'donor__paypalemail', 'donor__alias', 'donor__firstname', 'donor__lastname', 'amount')
  list_filter = ('event', 'transactionstate', 'readstate', 'commentstate', 'bidstate', DonationListFilter)
  raw_id_fields = ('donor','event');
  readonly_fields = ('domainId',);
  inlines = (ChoiceBidInline,ChallengeBidInline);
  def set_readstate_ignored(self, request, queryset):
    mass_assign_action(self, request, queryset, 'readstate', 'IGNORED');
  set_readstate_ignored.short_description = 'Set Read state to ignored.';
  def set_readstate_read(self, request, queryset):
    mass_assign_action(self, request, queryset, 'readstate', 'READ');
  set_readstate_read.short_description = 'Set Read state to read.';
  def set_commentstate_approved(self, request, queryset):
    mass_assign_action(self, request, queryset, 'commentstate', 'APPROVED');
  set_commentstate_approved.short_description = 'Set Comment state to approved.';
  def set_commentstate_denied(self, request, queryset):
    mass_assign_action(self, request, queryset, 'commentstate', 'DENIED');
  set_commentstate_denied.short_description = 'Set Comment state to denied.';
  def cleanup_orphaned_donations(self, request, queryset):
    count = 0;
    for donation in queryset.filter(donor=None, domain='PAYPAL', transactionstate='PENDING', timereceived__lte=datetime.utcnow() - timedelta(hours=8)):
      donor = donation.donor;
      donor.delete();
      count += 1;
    self.message_user(request, "Deleted %d donations." % count);
  cleanup_orphaned_donations.short_description = 'Clear out incomplete donations.';

  actions = [set_readstate_ignored, set_readstate_read, set_commentstate_approved, set_commentstate_denied, cleanup_orphaned_donations];

class DonorAdmin(CustomModelAdmin):
  search_fields = ('email', 'paypalemail', 'alias', 'firstname', 'lastname');
  list_filter = ('donation__event', 'issurrogate')
  fieldsets = [
    (None, { 'fields': ['email', 'alias', 'firstname', 'lastname', 'visibility', 'issurrogate'] }),
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
  def merge_donors(self, request, queryset):
    donors = queryset;
    donorIds = [str(o.id) for o in donors];
    return HttpResponseRedirect('/admin/merge_donors?donors=' + ','.join(donorIds));
  merge_donors.short_description = "Merge selected donors";
  actions = [merge_donors];

def merge_donors_view(request, *args, **kwargs):
  if request.method == 'POST':
    donors = map(lambda x: int(x), request.POST['donors'].split(','));
    form = forms.RootDonorForm(donors=donors, data=request.POST);
    if form.is_valid():
      root = tracker.models.Donor.objects.get(id=form.cleaned_data['rootdonor']);
      for other in donors:
        otherDonor = tracker.models.Donor.objects.get(id=other);
        if other != root:
          for donation in otherDonor.donation_set.all():
            root.donation_set.add(donation);
          for prize in otherDonor.prize_set.all():
            root.prize_set.add(prize);
        otherDonor.delete();
      root.save();
      return HttpResponseRedirect('/admin/tracker/donor');
  else:
    donors = map(lambda x: int(x), request.GET['donors'].split(','));
    form = forms.RootDonorForm(donors=donors);
  return render(request, 'admin/merge_donors.html', dictionary={'form': form})


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
      'fields': ['scheduleid', 'scheduletimezone', 'scheduledatetimefield', 'schedulegamefield', 'schedulerunnersfield', 'scheduleestimatefield', 'schedulesetupfield', 'schedulecommentatorsfield', 'schedulecommentsfield']
    }),
  ];
  def merge_schedule(self, request, queryset):
    for event in queryset:
      numRuns = viewutil.MergeScheduleGDoc(event);
      self.message_user(request, "%d runs merged for %s." % (numRuns, event.name));
  merge_schedule.short_description = "Merge schedule for event (please select only one)";
  actions = [merge_schedule];

class PrizeInline(CustomStackedInline):
  model = tracker.models.Prize
  fk_name = 'endrun'
  raw_id_fields = ['startrun', 'endrun', 'winner', 'event', 'contributors'];
  extra = 0;
  readonly_fields = ('edit_link',);

class PrizeAdmin(CustomModelAdmin):
  list_display = ('name', 'category', 'sortkey', 'bidrange', 'games', 'starttime', 'endtime', 'sumdonations', 'randomdraw', 'event', 'winner' )
  list_filter = ('event', 'category', PrizeListFilter)
  fieldsets = [
    (None, { 'fields': ['name', 'description', 'image', 'sortkey', 'event', 'deprecated_provided', 'contributors', 'winner', 'category'] }),
    ('Drawing Parameters', {
      'classes': ['collapse'],
      'fields': ['minimumbid', 'maximumbid', 'sumdonations', 'randomdraw', 'startrun', 'endrun', 'starttime', 'endtime']
    }),
  ]
  search_fields = ('name', 'description', 'provided', 'winner__firstname', 'winner__lastname', 'winner__alias', 'winner__email')
  raw_id_fields = ['startrun', 'endrun', 'winner', 'event', 'contributors']
  def bidrange(self, obj):
    s = unicode(obj.minimumbid)
    if obj.minimumbid != obj.maximumbid:
      s += ' <--> ' + unicode(obj.maximumbid)
    return s
  bidrange.short_description = 'Bid Range'
  def games(self, obj):
    if obj.startrun == None:
      return u'';
    else:
      s = unicode(obj.startrun.name)
      if obj.startrun != obj.endrun:
        s += ' <--> ' + unicode(obj.endrun.name)
  def draw_prize_action(self, request, queryset):
    numDrawn = 0;
    for prize in queryset:
      if prize.winner is None:
        drawn, msg = viewutil.draw_prize(prize);
        if not drawn:
          self.message_user(request, msg, level=messages.ERROR);
        else:
          numDrawn += 1;
      else:
        self.message_user(request, "Prize: " + str(prize) + " already has a winner.", level=messages.ERROR);
    if numDrawn > 0:
      self.message_user(request, "%d prizes drawn." % numDrawn);
  draw_prize_action.short_description = "Draw a winner for the selected prizes";
  actions = [draw_prize_action];

class SpeedRunAdmin(CustomModelAdmin):
  search_fields = ['name', 'description', 'runners__lastname', 'runners__firstname', 'runners__alias', 'deprecated_runners']
  list_filter = ['event', RunListFilter]
  inlines = [ChoiceInline, ChallengeInline,PrizeInline]
  fieldsets = [(None, { 'fields': ('name', 'description', 'sortkey', 'event', 'starttime', 'endtime', 'deprecated_runners', 'runners') }),];
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
