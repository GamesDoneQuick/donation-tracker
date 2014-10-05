from django.contrib import admin
import settings
import tracker.viewutil as viewutil
import tracker.views as views
import tracker.forms as forms
import tracker.models
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.utils.html import escape
from django.utils.text import Truncator
from django.utils.safestring import mark_safe
from django.contrib.admin import widgets
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.widgets import ManyToManyRawIdWidget
from django.utils.encoding import smart_unicode
from django.utils.html import escape
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.shortcuts import render, redirect
import django.forms as djforms
import filters
from datetime import *
import time

try:
	import adminplus
except ImportError:
	raise ImproperlyConfigured("Couldn't find adminplus package, please install it")

from ajax_select import make_ajax_field

def reverse_lazy(url):
	return lambda: reverse(url)

def make_admin_ajax_field(model,model_fieldname,channel,show_help_text = False,**kwargs):
  kwargs['is_admin'] = True
  return make_ajax_field(model, model_fieldname, channel, show_help_text=show_help_text, **kwargs)

def latest_event_id():
  try:
    return tracker.models.Event.objects.latest().id
  except tracker.models.Event.DoesNotExist:
    return 0

# todo: apply this to the ajax_selects and push it back to UA's repo
# http://djangosnippets.org/snippets/2217/
class VerboseManyToManyRawIdWidget(widgets.ManyToManyRawIdWidget):
    def label_for_value(self, value):
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
        return u', '.join(str_values)
      else:
        return super(VerboseManyToManyRawIdWidget, self).label_for_value(value)

class VerboseForeignKeyRawIdWidget(widgets.ForeignKeyRawIdWidget):
  def url_parameters(self):
    params = super(VerboseForeignKeyRawIdWidget, self).url_parameters()
    # TODO: have it splice in the 'event' parameter to the navigation url under some nebulous conditions
    return params
  def label_for_value(self, value):
    key = self.rel.get_related_field().name
    if self.rel.to in self.admin_site._registry:
      try:
        obj = self.rel.to._default_manager.using(self.db).get(**{key: value})
        text = '<strong>%s</strong>' % escape(Truncator(obj).words(14, truncate='...'))
        href = reverse('admin:%s_%s_change' % (obj._meta.app_label, obj._meta.module_name), args=(obj.pk,), current_app=self.admin_site.name)
        return '&nbsp;' + ('<a href=%s>' % href) + text + '</a>'
      except (ValueError, self.rel.to.DoesNotExist):
        return u'???'
    else:
      return super(VerboseForeignKeyRawIdWidget, self).label_for_value(value)

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
    return _formfield_for_dbfield(self, CustomModelAdmin, db_field, **kwargs)

# I don't think there's any other way around this, since I need the functionality in both of them
class CustomStackedInline(admin.StackedInline):
  def formfield_for_dbfield(self, db_field, **kwargs):
    return _formfield_for_dbfield(self, CustomStackedInline, db_field, **kwargs)
  def edit_link(self, instance):
    if instance.id != None:
      url = reverse('admin:{l}_{m}_change'.format(l=instance._meta.app_label,m=instance._meta.module_name), args=[instance.id])
      return mark_safe(u'<a href="{u}">Edit</a>'.format(u=url))
    else:
      return mark_safe(u'Not Saved Yet')

def ReadOffsetTokenPair(value):
  toks = value.split('-')
  feed = toks[0]
  params = {}
  if len(toks) > 1:
    params['delta'] = toks[1]
  return feed, params

class DonationListFilter(SimpleListFilter):
  title = 'feed'
  parameter_name = 'feed'
  def lookups(self, request, model_admin):
    return (('toprocess', 'To Process'), ('toread', 'To Read'), ('recent-5', 'Last 5 Minutes'), ('recent-10','Last 10 Minutes'), ('recent-30','Last 30 Minutes'), ('recent-60','Last Hour'), ('recent-180','Last 3 Hours'),)
  def queryset(self, request, queryset):
    if self.value() is not None:
      feed, params = ReadOffsetTokenPair(self.value())
      return filters.apply_feed_filter(queryset, 'donation', feed, params, user=request.user, noslice=True)
    else:
      return queryset

class BidListFilter(SimpleListFilter):
  title = 'feed'
  parameter_name = 'feed'
  def lookups(self, request, model_admin):
    return (('current', 'Current'), ('future', 'Future'), ('open','Open'), ('closed', 'Closed'))
  def queryset(self, request, queryset):
    if self.value() is not None:
      feed, params = ReadOffsetTokenPair(self.value())
      return filters.apply_feed_filter(queryset, 'bid', feed, params, request.user, noslice=True)
    else:
      return queryset

class BidParentFilter(SimpleListFilter):
  title = 'top level'
  parameter_name = 'toplevel'
  def lookups(self, request, model_admin):
    return ((1, 'Yes'), (0, 'No'))
  def queryset(self, request, queryset):
    try:
      queryset = queryset.filter(parent__isnull=True if int(self.value()) == 1 else False)
    except TypeError,ValueError: # self.value cannot be converted to int for whatever reason
      pass
    return queryset

class BidSuggestionListFilter(SimpleListFilter):
  title = 'feed'
  parameter_name = 'feed'
  def lookups(self, request, model_admin):
    return (('expired', 'Expired'),)
  def queryset(self, request, queryset):
    if self.value() is not None:
      feed, params = ReadOffsetTokenPair(self.value())
      return filters.apply_feed_filter(queryset, 'bidsuggestion', feed, params, request.user, noslice=True)
    else:
      return queryset

class RunListFilter(SimpleListFilter):
  title = 'feed'
  parameter_name = 'feed'
  def lookups(self, request, model_admin):
    return (('current','Current'), ('future', 'Future'), ('recent-60', 'Last Hour'), ('recent-180', 'Last 3 Hours'), ('recent-300', 'Last 5 Hours'), ('future-60', 'Next Hour'), ('future-180', 'Next 3 Hours'), ('future-300', 'Next 5 Hours'))
  def queryset(self, request, queryset):
    if self.value() is not None:
      feed, params = ReadOffsetTokenPair(self.value())
      return filters.apply_feed_filter(queryset, 'run', feed, params, user=request.user, noslice=True)
    else:
      return queryset

class PrizeListFilter(SimpleListFilter):
  title = 'feed'
  parameter_name = 'feed'
  def lookups(self, request, model_admin):
    return (('unwon', 'Not Drawn'), ('won', 'Drawn'), ('current', 'Current'), ('future', 'Future'), ('todraw', 'Ready To Draw'))
  def queryset(self, request, queryset):
    if self.value() is not None:
      feed, params = ReadOffsetTokenPair(self.value())
      return filters.apply_feed_filter(queryset, 'prize', feed, params, request.user, noslice=True)
    else:
      return queryset

def bid_open_action(modeladmin, request, queryset):
  bid_set_state_action(modeladmin, request, queryset, 'OPENED')
bid_open_action.short_description = "Set Bids as OPENED"

def bid_close_action(modeladmin, request, queryset):
  bid_set_state_action(modeladmin, request, queryset, 'CLOSED')
bid_close_action.short_description = "Set Bids as CLOSED"

def bid_hidden_action(modeladmin, request, queryset):
  bid_set_state_action(modeladmin, request, queryset, 'HIDDEN')
bid_hidden_action.short_description = "Set Bids as HIDDEN"

def bid_set_state_action(modeladmin, request, queryset, value, recursive=False):
  if not request.user.has_perm('tracker.can_edit_locked_event'):
    unchanged = queryset.filter(event__locked=True)
    if unchanged.exists():
      messages.warning(request, '%d bid(s) unchanged due to the event being locked.' % unchanged.count())
    queryset = queryset.filter(event__locked=False)
  if not recursive:
    unchanged = queryset.filter(parent__isnull=False)
    if unchanged.exists():
      messages.warning(request, '%d bid(s) possibly unchanged because you can only use the dropdown on top level bids.' % unchanged.count())
    queryset = queryset.filter(parent__isnull=True)
  total = queryset.count()
  for b in queryset:
    b.state = value
    total += bid_set_state_action(modeladmin, request, b.options.all(), value, True) # apply it to all the children too
    b.save() # can't use queryset.update because that doesn't send the post_save signals
  if total and not recursive:
    messages.success(request, '%d bid(s) changed to %s.' % (total,value))
  return total

class BidForm(djforms.ModelForm):
  speedrun = make_admin_ajax_field(tracker.models.Bid, 'speedrun', 'run')
  event = make_admin_ajax_field(tracker.models.Bid, 'event', 'event', initial=latest_event_id)
  biddependency = make_admin_ajax_field(tracker.models.Bid, 'biddependency', 'allbids')

class BidInline(CustomStackedInline):
  model = tracker.models.Bid
  fieldsets = [(None, {
    'fields': ['name', 'description', 'istarget', 'goal', 'state', 'total', 'edit_link'],
  },)]
  extra = 0
  readonly_fields = ('total','edit_link',)
  ordering = ('-total', 'name')

class BidOptionInline(BidInline):
  verbose_name_plural = 'Options'
  verbose_name = 'Option'
  fk_name = 'parent'
  
class BidDependentsInline(BidInline):
  verbose_name_plural = 'Dependent Bids'
  verbose_name = 'Dependent Bid'
  fk_name = 'biddependency'


class BidAdmin(CustomModelAdmin):
  form = BidForm
  list_display = ('name', 'parentlong', 'istarget', 'goal', 'total', 'description', 'state', 'biddependency')
  list_display_links = ('parentlong', 'biddependency')
  search_fields = ('name', 'speedrun__name', 'description', 'parent__name')
  list_filter = ('speedrun__event', 'state', 'istarget', BidParentFilter, BidListFilter)
  raw_id_fields = ('biddependency',)
  readonly_fields = ('parent','total')
  actions = [bid_open_action, bid_close_action, bid_hidden_action]
  inlines = [BidOptionInline, BidDependentsInline]
  def parentlong(self, obj):
    return unicode(obj.parent or obj.speedrun or obj.event)
  parentlong.short_description = 'Parent'
  def queryset(self, request):
    event = viewutil.get_selected_event(request)
    params = {}
    if event:
      params['event'] = event.id
    if not request.user.has_perm('tracker.can_edit_locked_events'):
      params['locked'] = False
    return filters.run_model_query('allbids', params, user=request.user, mode='admin')
  def has_add_permission(self, request):
    return request.user.has_perm('tracker.top_level_bid')
  def has_change_permission(self, request, obj=None):
    return obj == None or request.user.has_perm('tracker.can_edit_locked_events') or not obj.event.locked
  def has_delete_permission(self, request, obj=None):
    return obj == None or \
       ((request.user.has_perm('tracker.can_edit_locked_events') or not obj.event.locked) and \
        (request.user.has_perm('tracker.delete_all_bids') or not obj.total))
  def get_actions(self, request):
    actions = super(BidAdmin, self).get_actions(request)
    if not request.user.has_perm('tracker.delete_all_bids') and 'delete_selected' in actions:
      del actions['delete_selected']
    return actions

class BidSuggestionForm(djforms.ModelForm):
  bid = make_admin_ajax_field(tracker.models.BidSuggestion, 'bid', 'bidtarget')

class BidSuggestionAdmin(CustomModelAdmin):
  form = BidSuggestionForm
  list_display = ('name', 'bid')
  search_fields = ('name', 'bid__name', 'bid__description')
  list_filter = ('bid__state', 'bid__speedrun__event', 'bid__event', BidSuggestionListFilter)
  def queryset(self, request):
    event = viewutil.get_selected_event(request)
    params = {}
    if not request.user.has_perm('tracker.can_edit_locked_events'):
      params['locked'] = False
    if event:
      params['event'] = event.id
    return filters.run_model_query('bidsuggestion', params, user=request.user, mode='admin')

class DonationBidForm(djforms.ModelForm):
  bid = make_admin_ajax_field(tracker.models.DonationBid, 'bid', 'bidtarget', add_link=reverse_lazy('admin:tracker_bid_add'))
  donation = make_admin_ajax_field(tracker.models.DonationBid, 'donation', 'donation')

class DonationBidInline(CustomStackedInline):
  form = DonationBidForm
  model = tracker.models.DonationBid
  extra = 0
  max_num=100
  readonly_fields = ('edit_link',)

class DonationBidForm(djforms.ModelForm):
  bid = make_admin_ajax_field(tracker.models.DonationBid, 'bid', 'bidtarget', add_link=reverse_lazy('admin:tracker_bid_add'))
  donation = make_admin_ajax_field(tracker.models.DonationBid, 'donation', 'donation')

class DonationBidAdmin(CustomModelAdmin):
  form = DonationBidForm
  list_display = ('bid', 'donation', 'amount')
  def queryset(self, request):
    event = viewutil.get_selected_event(request)
    params = {}
    if not request.user.has_perm('tracker.can_edit_locked_events'):
      params['locked'] = False
    if event:
      params['event'] = event.id
    return filters.run_model_query('donationbid', params, user=request.user, mode='admin')

class DonationForm(djforms.ModelForm):
  donor = make_admin_ajax_field(tracker.models.Donation, 'donor', 'donor', add_link=reverse_lazy('admin:tracker_donor_add'))
  event = make_admin_ajax_field(tracker.models.Donation, 'event', 'event', initial=latest_event_id)
  class Meta:
    model = tracker.models.Donation

class DonationInline(CustomStackedInline):
  form = DonationForm
  model = tracker.models.Donation
  raw_id_fields = ('donor',)
  extra = 0
  readonly_fields = ('edit_link',)

def mass_assign_action(self, request, queryset, field, value):
  queryset.update(**{ field: value })
  self.message_user(request, "Updated %s to %s" % (field, value))

class PrizeTicketInline(CustomStackedInline):
  model = tracker.models.PrizeTicket
  fk_name = 'donation'
  raw_id_fields = ('prize',)
  extra = 0
  readonly_fields = ('edit_link',)

class DonationAdmin(CustomModelAdmin):
  form = DonationForm
  list_display = ('donor', 'visible_donor_name', 'amount', 'comment', 'commentlanguage', 'timereceived', 'event', 'domain', 'transactionstate', 'bidstate', 'readstate', 'commentstate',)
  list_editable = ('transactionstate', 'bidstate', 'readstate', 'commentstate')
  search_fields = ('donor__email', 'donor__paypalemail', 'donor__alias', 'donor__firstname', 'donor__lastname', 'amount', 'comment', 'modcomment')
  list_filter = ('event', 'transactionstate', 'readstate', 'commentstate', 'bidstate', 'commentlanguage', DonationListFilter)
  readonly_fields = ['domainId']
  inlines = (DonationBidInline,PrizeTicketInline)
  fieldsets = [
    (None, {'fields': ('donor', 'event', 'timereceived')}),
    ('Comment State', {'fields': ('comment', 'modcomment')}),
    ('Donation State', {'fields': (('transactionstate', 'bidstate', 'readstate', 'commentstate'),)}),
    ('Financial', {'fields': (('amount', 'fee', 'currency', 'testdonation'),)}),
    ('Extra Donor Info', {'fields': (('requestedvisibility', 'requestedalias', 'requestedemail'),)}),
    ('Other', {'fields': (('domain', 'domainId'),)}),
  ]
  def visible_donor_name(self, obj):
    if obj.donor:
      return obj.donor.visible_name()
    else:
      return None
  def set_readstate_ready(self, request, queryset):
    mass_assign_action(self, request, queryset, 'readstate', 'READY')
  set_readstate_ready.short_description = 'Set Read state to ready to read.'
  def set_readstate_ignored(self, request, queryset):
    mass_assign_action(self, request, queryset, 'readstate', 'IGNORED')
  set_readstate_ignored.short_description = 'Set Read state to ignored.'
  def set_readstate_read(self, request, queryset):
    mass_assign_action(self, request, queryset, 'readstate', 'READ')
  set_readstate_read.short_description = 'Set Read state to read.'
  def set_commentstate_approved(self, request, queryset):
    mass_assign_action(self, request, queryset, 'commentstate', 'APPROVED')
  set_commentstate_approved.short_description = 'Set Comment state to approved.'
  def set_commentstate_denied(self, request, queryset):
    mass_assign_action(self, request, queryset, 'commentstate', 'DENIED')
  set_commentstate_denied.short_description = 'Set Comment state to denied.'
  def cleanup_orphaned_donations(self, request, queryset):
    count = 0
    for donation in queryset.filter(donor=None, domain='PAYPAL', transactionstate='PENDING', timereceived__lte=datetime.utcnow() - timedelta(hours=8)):
      donor = donation.donor
      donor.delete()
      count += 1
    self.message_user(request, "Deleted %d donations." % count)
  cleanup_orphaned_donations.short_description = 'Clear out incomplete donations.'
  def get_list_display(self, request):
    ret = list(self.list_display)
    if not request.user.has_perm('tracker.delete_all_donations'):
      ret.remove('transactionstate')
    return ret
  def get_readonly_fields(self, request, obj=None):
    perm = request.user.has_perm('tracker.delete_all_donations')
    ret = list(self.readonly_fields)
    if not perm:
      ret.append('domain')
      ret.append('fee')
      ret.append('transactionstate')
      ret.append('testdonation')
      if obj and obj.domain != 'LOCAL':
        ret.append('donor')
        ret.append('event')
        ret.append('timereceived')
        ret.append('amount')
        ret.append('currency')
    return ret
  def has_change_permission(self, request, obj=None):
    return obj == None or request.user.has_perm('tracker.can_edit_locked_events') or not obj.event.locked
  def has_delete_permission(self, request, obj=None):
    return obj == None or obj.domain == 'LOCAL' or request.user.has_perm('tracker.delete_all_donations')
  def queryset(self, request):
    event = viewutil.get_selected_event(request)
    params = {}
    if not request.user.has_perm('tracker.can_edit_locked_events'):
      params['locked'] = False
    if event:
      params['event'] = event.id
    return filters.run_model_query('donation', params, user=request.user, mode='admin')
  actions = [set_readstate_ready, set_readstate_ignored, set_readstate_read, set_commentstate_approved, set_commentstate_denied, cleanup_orphaned_donations]
  def get_actions(self, request):
    actions = super(DonationAdmin, self).get_actions(request)
    if not request.user.has_perm('tracker.delete_all_donations') and 'delete_selected' in actions:
      del actions['delete_selected']
    return actions

class PrizeWinnerForm(djforms.ModelForm):
  winner = make_admin_ajax_field(tracker.models.PrizeWinner, 'winner', 'donor')
  prize = make_admin_ajax_field(tracker.models.PrizeWinner, 'prize', 'prize')
  class Meta:
    model = tracker.models.PrizeWinner

class PrizeWinnerInline(CustomStackedInline):
  form = PrizeWinnerForm
  model = tracker.models.Prize.winners.through
  raw_id_fields = ['winner', 'prize',]
  extra = 0

class DonorAdmin(CustomModelAdmin):
  search_fields = ('email', 'paypalemail', 'alias', 'firstname', 'lastname')
  list_filter = ('donation__event', 'visibility')
  readonly_fields = (('visible_name'),)
  list_display = ('__unicode__', 'visible_name', 'alias', 'visibility')
  fieldsets = [
    (None, { 'fields': ['email', 'alias', 'firstname', 'lastname', 'visibility', 'visible_name'] }),
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
  ]
  inlines = [DonationInline, PrizeWinnerInline]
  def visible_name(self, obj):
    return obj.visible_name()
  def merge_donors(self, request, queryset):
    donors = queryset
    donorIds = [str(o.id) for o in donors]
    return HttpResponseRedirect('/admin/merge_donors?donors=' + ','.join(donorIds))
  merge_donors.short_description = "Merge selected donors"
  actions = [merge_donors]

def merge_donors_view(request, *args, **kwargs):
  if request.method == 'POST':
    donors = map(lambda x: int(x), request.POST['donors'].split(','))
    form = forms.RootDonorForm(donors=donors, data=request.POST)
    if form.is_valid():
      root = tracker.models.Donor.objects.get(id=form.cleaned_data['rootdonor'])
      for other in donors:
        otherDonor = tracker.models.Donor.objects.get(id=other)
        if other != root:
          for donation in otherDonor.donation_set.all():
            root.donation_set.add(donation)
          for prize in otherDonor.prize_set.all():
            root.prize_set.add(prize)
        otherDonor.delete()
      root.save()
      return HttpResponseRedirect('admin:tracker_donor')
  else:
    donors = map(lambda x: int(x), request.GET['donors'].split(','))
    form = forms.RootDonorForm(donors=donors)
  return render(request, 'admin/merge_donors.html', dictionary={'form': form})


class EventAdmin(CustomModelAdmin):
  search_fields = ('short', 'name')
  inlines = [BidInline]
  list_display = ['name', 'locked']
  list_editable = ['locked']
  fieldsets = [
    (None, { 'fields': ['short', 'name', 'receivername', 'targetamount', 'date', 'locked'] }),
    ('Paypal', {
      'classes': ['collapse'],
      'fields': ['paypalemail', 'usepaypalsandbox', 'paypalcurrency']
    }),
    ('Google Document', {
      'classes': ['collapse'],
      'fields': ['scheduleid', 'scheduletimezone', 'scheduledatetimefield', 'schedulegamefield', 'schedulerunnersfield', 'scheduleestimatefield', 'schedulesetupfield', 'schedulecommentatorsfield', 'schedulecommentsfield']
    }),
    ('Prize Mailing', {
      'classes': ['collapse'],
      'fields': ['prizemailsubject', 'prizemailbody']
    }),
  ]
  def merge_schedule(self, request, queryset):
    for event in queryset:
      numRuns = viewutil.merge_schedule_gdoc(event)
      self.message_user(request, "%d runs merged for %s." % (numRuns, event.name))
  merge_schedule.short_description = "Merge schedule for event (please select only one)"
  actions = [merge_schedule]

class PostbackURLForm(djforms.ModelForm):
  event = make_admin_ajax_field(tracker.models.PostbackURL, 'event', 'event', initial=latest_event_id)
  class Meta:
    model = tracker.models.PostbackURL

class PostbackURLAdmin(CustomModelAdmin):
  form = PostbackURLForm
  search_fields = ('url',)
  list_filter = ('event',)
  list_display = ('url', 'event')
  fieldsets = [
    (None, { 'fields': ['event', 'url'] })
  ]
  def queryset(self, request):
    event = viewutil.get_selected_event(request)
    if event:
      return tracker.models.PostbackURL.objects.filter(event=event)
    else:
      return tracker.models.PostbackURL.objects.all()

class PrizeInline(CustomStackedInline):
  model = tracker.models.Prize
  fk_name = 'endrun'
  raw_id_fields = ['startrun', 'endrun', 'winners', 'event', ]
  extra = 0
  readonly_fields = ('edit_link',)

class PrizeForm(djforms.ModelForm):
  event = make_admin_ajax_field(tracker.models.Prize, 'event', 'event', initial=latest_event_id)
  startrun = make_admin_ajax_field(tracker.models.Prize, 'startrun', 'run')
  endrun = make_admin_ajax_field(tracker.models.Prize, 'endrun', 'run')
  class Meta:
    model = tracker.models.Prize

class PrizeAdmin(CustomModelAdmin):
  form = PrizeForm
  list_display = ('name', 'category', 'bidrange', 'games', 'starttime', 'endtime', 'sumdonations', 'randomdraw', 'event', 'winners_' )
  list_filter = ('event', 'category', PrizeListFilter)
  fieldsets = [
    (None, { 'fields': ['name', 'description', 'image', 'event', 'provided', 'creator', 'creatoremail', 'creatorwebsite', 'state', 'category', ] }),
    ('Drawing Parameters', {
      'classes': ['collapse'],
      'fields': ['maxwinners', 'minimumbid', 'maximumbid', 'sumdonations', 'randomdraw', 'ticketdraw', 'startrun', 'endrun', 'starttime', 'endtime']
    }),
  ]
  search_fields = ('name', 'description', 'provided', 'winners__firstname', 'winners__lastname', 'winners__alias', 'winners__email')
  raw_id_fields = ['event']
  inlines = [PrizeWinnerInline]
  def winners_(self, obj):
    if obj.winners.exists():
      return reduce(lambda x,y: x + " ; " + y, map(lambda x: unicode(x), obj.winners.all()))
    else:
      return 'None'
  def bidrange(self, obj):
    s = unicode(obj.minimumbid)
    if obj.minimumbid != obj.maximumbid:
      if obj.maximumbid == None:
        max = u'Infinite'
      else:
        max = unicode(obj.maximumbid)
      s += ' <--> ' + max
    return s
  bidrange.short_description = 'Bid Range'
  def games(self, obj):
    if obj.startrun == None:
      return u''
    else:
      s = unicode(obj.startrun.name)
      if obj.startrun != obj.endrun:
        s += ' <--> ' + unicode(obj.endrun.name)
  def draw_prize_internal(self, request, queryset, limit):
    numDrawn = 0
    for prize in queryset:
      if not limit:
        limit = prize.maxwinners;
      drawingError = False
      while not drawingError and prize.winners.count() < limit:
        drawn, msg = viewutil.draw_prize(prize)
        time.sleep(1)
        if not drawn:
          self.message_user(request, msg, level=messages.ERROR)
          drawingError = True
        else:
          numDrawn += 1
    if numDrawn > 0:
      self.message_user(request, "%d prizes drawn." % numDrawn)
  def draw_prize_once_action(self, request, queryset):
    draw_prize_internal(self, request, queryset, 1)
  draw_prize_once_action.short_description = "Draw a SINGLE winner for the selected prizes"
  def draw_prize_action(self, request, queryset):
    draw_prize_internal(self, request, queryset, 0)
  draw_prize_action.short_description = "Draw (all) winner(s) for the selected prizes"
  actions = [draw_prize_action, draw_prize_once_action]
  def queryset(self, request):
    event = viewutil.get_selected_event(request)
    params = {}
    if not request.user.has_perm('tracker.can_edit_locked_events'):
      params['locked'] = False
    if event:
      params['event'] = event.id
    return filters.run_model_query('prize', params, user=request.user, mode='admin')

class PrizeTicketForm(djforms.ModelForm):
  prize = make_admin_ajax_field(tracker.models.PrizeTicket, 'prize', 'prize', add_link=reverse_lazy('admin:tracker_prize_add'))
  donation = make_admin_ajax_field(tracker.models.PrizeTicket, 'donation', 'donation')

class PrizeTicketAdmin(CustomModelAdmin):
  form = PrizeTicketForm
  list_display = ('prize', 'donation', 'amount')
  def queryset(self, request):
    event = viewutil.get_selected_event(request)
    params = {}
    if not request.user.has_perm('tracker.can_edit_locked_events'):
      params['locked'] = False
    if event:
      params['event'] = event.id
    return filters.run_model_query('prizeticket', params, user=request.user, mode='admin')

class SpeedRunAdminForm(djforms.ModelForm):
  event = make_admin_ajax_field(tracker.models.SpeedRun, 'event', 'event', initial=latest_event_id)
  runners = make_admin_ajax_field(tracker.models.SpeedRun, 'runners', 'donor')
  class Meta:
    model = tracker.models.SpeedRun

class SpeedRunAdmin(CustomModelAdmin):
  form = SpeedRunAdminForm
  search_fields = ['name', 'description', 'runners__lastname', 'runners__firstname', 'runners__alias', 'deprecated_runners']
  list_filter = ['event', RunListFilter]
  inlines = [BidInline,PrizeInline]
  fieldsets = [(None, { 'fields': ('name', 'description', 'event', 'starttime', 'endtime', 'deprecated_runners', 'runners') }),]
  readonly_fields = ('name', 'deprecated_runners')
  def queryset(self, request):
    event = viewutil.get_selected_event(request)
    params = {}
    if not request.user.has_perm('tracker.can_edit_locked_events'):
      params['locked'] = False
    if event:
      params['event'] = event.id
    return filters.run_model_query('run', params, user=request.user, mode='admin')

def select_event(request):
  current = viewutil.get_selected_event(request)
  if request.method == 'POST':
    form = forms.EventFilterForm(data=request.POST)
    if form.is_valid():
      viewutil.set_selected_event(request, form.cleaned_data['event'])
      return redirect('admin:index')
  else:
    form = forms.EventFilterForm({'event': current})
  return render(request, 'admin/select_event.html', { 'form': form })

def show_completed_bids(request):
  current = viewutil.get_selected_event(request)
  params = {'state': 'OPENED'}
  if current:
    params['event'] = current.id
  bids = filters.run_model_query('allbids', params, user=request.user, mode='admin')
  bids = viewutil.get_tree_queryset_descendants(tracker.models.Bid, bids, include_self=True).annotate(**viewutil.ModelAnnotations['bid'])
  bids = viewutil.FixupBidAnnotations(bids)
  bidList = []
  for bidK in bids:
    bid = bids[bidK]
    if bid.state == 'OPENED' and bid.goal and bid.amount > bid.goal:
      bidList.append(bid)
  if request.method == 'POST':
    for bid in bidList:
      bid.state = 'CLOSED'
      bid.save()
    return render(request, 'admin/completed_bids_post.html', { 'bids': bidList })
  return render(request, 'admin/completed_bids.html', { 'bids': bidList })

def process_donations(request):
  current = viewutil.get_selected_event(request)
  currentEvent = 'null'
  if current:
    currentEvent = current.id
  return render(request, 'admin/process_donations.html', { 'currentEvent': currentEvent })

def read_donations(request):
  current = viewutil.get_selected_event(request)
  currentEvent = 'null'
  if current:
    currentEvent = current.id
  return render(request, 'admin/read_donations.html', { 'currentEvent': currentEvent })
  
def process_prize_submissions(request):
  current = viewutil.get_selected_event(request)
  currentEvent = 'null'
  if current:
    currentEvent = current.id
  return render(request, 'admin/process_prize_submissions.html', { 'currentEvent': currentEvent })

# http://stackoverflow.com/questions/2223375/multiple-modeladmins-views-for-same-model-in-django-admin
# viewName - what to call the model in the admin
# model - the model to use
# modelAdmin - the model admin manager to use
def admin_register_surrogate_model(viewName, model, modelAdmin):
  class Meta:
    proxy = True
    app_label = model._meta.app_label
  attrs = {'__module__': '', 'Meta': Meta}
  newmodel = type(viewName, (model,), attrs)
  admin.site.register(newmodel, modelAdmin)
  return modelAdmin

#TODO: create a surrogate model for Donation with all of the default filters already set?

admin.site.register(tracker.models.Bid, BidAdmin)
admin.site.register(tracker.models.DonationBid, DonationBidAdmin)
admin.site.register(tracker.models.BidSuggestion, BidSuggestionAdmin)
admin.site.register(tracker.models.Donation, DonationAdmin)
admin.site.register(tracker.models.Donor, DonorAdmin)
admin.site.register(tracker.models.Event, EventAdmin)
admin.site.register(tracker.models.Prize, PrizeAdmin)
admin.site.register(tracker.models.PrizeTicket, PrizeTicketAdmin)
admin.site.register(tracker.models.PrizeCategory)
admin.site.register(tracker.models.SpeedRun, SpeedRunAdmin)
admin.site.register(tracker.models.UserProfile)
admin.site.register(tracker.models.PostbackURL, PostbackURLAdmin)

try:
  admin.site.register_view('select_event', name='Select an Event', urlname='select_event', view=select_event)
  admin.site.register_view('show_completed_bids', name='Show Completed Bids', urlname='show_completed_bids', view=show_completed_bids)
  admin.site.register_view('process_donations', name='Process Donations', urlname='process_donations', view=process_donations)
  admin.site.register_view('read_donations', name='Read Donations', urlname='read_donations', view=read_donations)
  admin.site.register_view('process_prize_submissions', name='Process Prize Submissions', urlname='process_prize_submissions', view=process_prize_submissions);
  admin.site.register_view('search_objects', name='search_objects', urlname='search_objects', view=views.search, visible=False)
  admin.site.register_view('edit_object', name='edit_object', urlname='edit_object', view=views.edit, visible=False)
  admin.site.register_view('add_object', name='add_object', urlname='add_object', view=views.add, visible=False)
  admin.site.register_view('delete_object', name='delete_object', urlname='delete_object', view=views.add, visible=False)
  # Apparently adminplus doesn't allow parameterized URLS (or at least, I'm not clear on how they work...)
  # -> the problem seems to be in the urls file, perhaps that I just need to edit that?
  admin.site.register_view('draw_prize', name='draw_prize', urlname='draw_prize', view=views.draw_prize, visible=False)
except AttributeError:
  raise ImproperlyConfigured("Couldn't call register_view on admin.site, make sure admin.site = AdminSitePlus() in urls.py")
