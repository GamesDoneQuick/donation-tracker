import django

from django import shortcuts
from django.shortcuts import render,render_to_response

from django.db import connection
from django.db.models import Count,Sum,Max,Avg,Q
from django.db.utils import ConnectionDoesNotExist

from django.core import serializers
from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.core.exceptions import FieldError

from django.contrib.auth import authenticate,login as auth_login,logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm

from django.http import HttpResponse,HttpResponseRedirect

from django import template
from django.template import RequestContext
from django.template.base import TemplateSyntaxError

from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from django.utils import translation
from django.utils import simplejson

from tracker.models import *
from tracker.forms import *

import sys
import datetime
import settings
import chipin

def dv():
	return str(django.VERSION[0]) + '.' + str(django.VERSION[1]) + '.' + str(django.VERSION[2])

def pv():
	return str(sys.version_info[0]) + '.' + str(sys.version_info[1]) + '.' + str(sys.version_info[2])

def fixorder(queryset, orderdict, sort, order):
	queryset = queryset.order_by(*orderdict[sort])
	if order == -1:
		queryset = queryset.reverse()
	return queryset

def redirect(request):
	return django.shortcuts.redirect('/tracker/')

@csrf_protect
@never_cache
def login(request):
	redirect_to = request.REQUEST.get('next', '/')
	if len(redirect_to) == 0 or redirect_to[0] != '/':
		redirect_to = '/' + redirect_to
	while redirect_to[:2] == '//':
		redirect_to = '/' + redirect_to[2:]
	if request.method == 'POST':
		form = AuthenticationForm(data=request.POST)
		if form.is_valid():
			auth_login(request, form.get_user())
	return django.shortcuts.redirect(redirect_to)

@never_cache
def logout(request):
	auth_logout(request)
	return django.shortcuts.redirect(request.META.get('HTTP_REFERER', '/'))

def tracker_response(request=None, template='tracker/index.html', dict={}, status=200):
	starttime = datetime.datetime.now()
	usernames = request.user.has_perm('tracker.view_usernames') and 'nonames' not in request.GET
	emails = request.user.has_perm('tracker.view_emails') and 'noemails' not in request.GET
	showtime = request.user.has_perm('tracker.show_rendertime')
	canfull = request.user.has_perm('tracker.view_full_list')
	bidtracker = request.user.has_perms([u'tracker.change_challenge', u'tracker.delete_challenge', u'tracker.change_choiceoption', u'tracker.delete_choice', u'tracker.delete_challengebid', u'tracker.add_choiceoption', u'tracker.change_choicebid', u'tracker.add_challengebid', u'tracker.add_choice', u'tracker.add_choicebid', u'tracker.delete_choiceoption', u'tracker.delete_choicebid', u'tracker.add_challenge', u'tracker.change_choice', u'tracker.change_challengebid'])
	context = RequestContext(request)
	language = translation.get_language_from_request(request)
	translation.activate(language)
	request.LANGUAGE_CODE = translation.get_language()
	profile = None
	if request.user.is_authenticated():
		try:
			profile = request.user.get_profile()
		except UserProfile.DoesNotExist:
			profile = UserProfile()
			profile.user = request.user
			profile.save()
	if profile:
		template = profile.prepend + template
		prepend = profile.prepend
	else:
		prepend = ''
	authform = AuthenticationForm(request.POST)
	dict.update({
		'dbtitle' : settings.DATABASES['default']['COMMENT'], # FIXME
		'usernames' : usernames,
		'emails' : emails,
		'canfull' : canfull,
		'bidtracker' : bidtracker,
		'djangoversion' : dv(),
		'pythonversion' : pv(),
		'user' : request.user,
		'profile' : profile,
		'prepend' : prepend,
		'next' : request.REQUEST.get('next', request.path),
		'showtime' : showtime,
		'starttime' : starttime,
		'authform' : authform })
	try:
		if request.user.username[:10]=='openiduser':
			dict.setdefault('usernameform', UsernameForm())
			return render(request, 'tracker/username.html', dictionary=dict)
		resp = render(request, template, dictionary=dict, status=status)
		if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
			return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
		return resp
	except Exception as e:
		if request.user.is_staff and not settings.DEBUG:
			return HttpResponse(unicode(type(e)) + '\n\n' + unicode(e), mimetype='text/plain', status=500)
		raise

def eventlist(request):
	return tracker_response(request, None, 'tracker/eventlist.html', { 'databases' : settings.DATABASES })

def index(request):
	agg = Donation.objects.filter(amount__gt="0.0").aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
	count = {
		'runs' : SpeedRun.objects.count(),
		'prizes' : Prize.objects.count(),
		'challenges' : Challenge.objects.count(),
		'choices' : Choice.objects.count(),
		'donors' : Donor.objects.count(),
	}
	return tracker_response(request, 'tracker/index.html', { 'agg' : agg, 'count' : count })

@never_cache
def setusername(request):
	if not request.user.is_authenticated or request.user.username[:10]!='openiduser' or request.method != 'POST':
		return redirect(request)
	usernameform = UsernameForm(request.POST)
	if usernameform.is_valid():
		request.user.username = request.POST['username']
		request.user.save()
		return shortcuts.redirect(request.POST['next'])
	return tracker_response(request, template='tracker/username.html', dict={ 'usernameform' : usernameform })

@never_cache
def search(request):
	if not request.user.has_perm('tracker.can_search'):
		return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
	try:
		searchtype = request.GET['type']
		qfilter = {}
		if 'event' in request.GET:
			qfilter['event__name'] = request.GET['event']
		modelmap = { 'challenge': Challenge,
			}
		general = { 'challenge': [ 'speedrun__name', 'name', 'description' ],
			}
		specific = { 
			'challenge': { 
				'run' : 'speedrun__name__icontains', 
				'name' : 'name__icontains',
				'description' : 'description__icontains',
				'state' : 'state'
			},
		}
		annotate = {
			'challenge': { 'total': Sum('bids__amount'), 'bidcount': Count('bids') }
		}
		qs = modelmap[searchtype].objects.annotate(**annotate[searchtype])
		if 'q' in request.GET:
			qf = Q(**{general[searchtype][0] + '__icontains': request.GET['q'] })
			for q in general[searchtype][1:]:
				qf |= Q(**{q + '__icontains': request.GET['q']})
			qs = qs.filter(qf)
		else:
			for key in specific[searchtype]:
				if key in request.GET:
					qfilter[specific[searchtype][key]] = request.GET[key]
		qs = qs.filter(**qfilter)
		json = simplejson.loads(serializers.serialize('json', qs, ensure_ascii=False))
		objs = dict(map(lambda o: (o.id,o), qs))
		for o in json:
			for a in annotate[searchtype]:
				o['fields'][a] = unicode(getattr(objs[int(o['pk'])],a))
		return HttpResponse(simplejson.dumps(json,ensure_ascii=False),content_type='application/json;charset=utf-8')
	except KeyError as e:
		return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed search parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	#except FieldError as e:
	#	return HttpResponse(simplejson.dumps({'error': 'Field Error, malformed search parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')	

def challengeindex(request):
	challenges = Challenge.objects.select_related('speedrun').annotate(amount=Sum('challengebid__amount'), count=Count('challengebid'))
	agg = ChallengeBid.objects.aggregate(amount=Sum('amount'), count=Count('amount'))
	return tracker_response(request, 'tracker/challengeindex.html', { 'challenges' : challenges, 'agg' : agg })
	
def challenge(request,id):
	try:
		orderdict = {
			'name'   : ('donation__donor__lastname', 'donation__donor__firstname'),
			'amount' : ('amount', ),
			'time'   : ('donation__timereceived', ),
		}
		sort = request.GET.get('sort', 'time')
		if sort not in orderdict:
			sort = 'time'
		try:
			order = int(request.GET.get('order', '-1'))
		except ValueError:
			order = -1
		challenge = Challenge.objects.get(pk=id)
		bids = ChallengeBid.objects.filter(challenge__exact=id).select_related('donation','donation__donor').order_by('-donation__timereceived')
		bids = fixorder(bids, orderdict, sort, order)
		comments = 'comments' in request.GET
		agg = ChallengeBid.objects.filter(challenge__exact=id).aggregate(amount=Sum('amount'), count=Count('amount'))
		return tracker_response(request, 'tracker/challenge.html', { 'challenge' : challenge, 'comments' : comments, 'bids' : bids, 'agg' : agg })
	except Challenge.ObjectDoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def choiceindex(request):
	choices = Choice.objects.values('id', 'name', 'speedrun', 'speedrun__sortkey', 'speedrun__name', 'option', 'option__name').annotate(amount=Sum('option__choicebid__amount'), count=Count('option__choicebid')).order_by('speedrun__sortkey','name','-amount','choiceoption__name')
	agg = ChoiceBid.objects.aggregate(amount=Sum('amount'), count=Count('amount'))
	return tracker_response(request, 'tracker/choiceindex.html', { 'choices' : choices, 'agg' : agg })

def choice(request,id):
	try:
		choice = Choice.objects.get(pk=id)
		choicebids = ChoiceBid.objects.filter(choiceOption__choice=id).values('ption', 'donation', 'donation__donor', 'donation__donor__lastname', 'donation__donor__firstname', 'donation__donor__email', 'donation__timereceived', 'donation__comment', 'donation__commentstate', 'amount').order_by('-donation__timereceived')
		options = ChoiceOption.objects.filter(choice=id).annotate(amount=Sum('choicebid__amount'), count=Count('choicebid__amount')).order_by('-amount')
		agg = ChoiceBid.objects.filter(choiceOption__choice=id).aggregate(amount=Sum('amount'), count=Count('amount'))
		comments = 'comments' in request.GET
		return tracker_response(request, 'tracker/choice.html', { 'choice' : choice, 'choicebids' : choicebids, 'comments' : comments, 'options' : options, 'agg' : agg })
	except Choice.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def choiceoption(request,id):
	try:
		orderdict = {
			'name'   : ('donation__donor__lastname', 'donation__donor__firstname'),
			'amount' : ('amount', ),
			'time'   : ('donation__timereceived', ),
		}
		sort = request.GET.get('sort', 'time')
		if sort not in orderdict:
			sort = 'time'
		try:
			order = int(request.GET.get('order', '-1'))
		except ValueError:
			order = -1
		choiceoption = ChoiceOption.objects.get(pk=id)
		agg = ChoiceBid.objects.filter(choiceOption=id).aggregate(amount=Sum('amount'))
		bids = ChoiceBid.objects.values('donation', 'donation__comment', 'donation__commentstate', 'donation__donor', 'donation__donor__firstname','donation__donor__lastname', 'donation__donor__email', 'amount', 'donation__timereceived').filter(choiceOption=id)
		bids = fixorder(bids, orderdict, sort, order)
		comments = 'comments' in request.GET
		return tracker_response(request, 'tracker/choiceoption.html', { 'choiceoption' : choiceoption, 'bids' : bids, 'comments' : comments, 'agg' : agg })
	except ChoiceOption.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def choicebidadd(request,id):
	return index(request)

def donorindex(request):
	orderdict = {
		'name'  : ('lastName', 'firstName'),
		'total' : ('amount',   ),
		'max'   : ('max',      ),
		'avg'   : ('avg',      )
	}
	try:
		page = int(request.GET.get('page', 1))
	except ValueError:
		page = 1
	sort = request.GET.get('sort', 'name')
	if sort not in orderdict:
		sort = 'name'
	try:
		order = int(request.GET.get('order', 1))
	except ValueError:
		order = 1
	database = checkdb(db)
	donors = Donor.objects.filter(lastName__isnull=False).annotate(amount=Sum('donation__amount'), count=Count('donation__amount'), max=Max('donation__amount'), avg=Avg('donation__amount'))
	print donors
	donors = fixorder(donors, orderdict, sort, order)
	fulllist = request.user.has_perm('tracker.view_full_list') and 'full' in request.GET
	paginator = Paginator(donors,50)
	if fulllist:
		pageinfo = { 'paginator' : paginator, 'has_previous' : False, 'has_next' : False, 'num_pages' : paginator.num_pages }
		page = 0
	else:
		try:
			pageinfo = paginator.page(page)
		except PageIsNotAnInteger:
			pageinfo = paginator.page(1)
		except EmptyPage:
			pageinfo = paginator.page(paginator.num_pages)
		donors = pageinfo.object_list
	agg = Donation.objects.filter(amount__gt="0.0").aggregate(count=Count('amount'))
	return tracker_response(request, 'tracker/donorindex.html', { 'donors' : donors, 'pageinfo' : pageinfo, 'page' : page, 'fulllist' : fulllist, 'agg' : agg, 'sort' : sort, 'order' : order })

def donor(request,id):
	try:
		donor = Donor.objects.get(pk=id)
		donations = Donation.objects.filter(donor__exact=id)
		comments = 'comments' in request.GET
		agg = donations.aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
		return tracker_response(request, 'tracker/donor.html', { 'donor' : donor, 'donations' : donations, 'agg' : agg, 'comments' : comments })
	except Donor.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def donationindex(request):
	orderdict = {
		'name'   : ('donor__lastName', 'donor__firstName'),
		'amount' : ('amount', ),
		'time'   : ('timereceived', ),
	}
	try:
		page = int(request.GET.get('page', 1))
	except ValueError:
		page = 1
	sort = request.GET.get('sort', 'time')
	if sort not in orderdict:
		sort = 'time'
	try:
		order = int(request.GET.get('order', -1))
	except ValueError:
		order = -1
	donations = Donation.objects.filter(amount__gt="0.0").values('id', 'domain', 'timereceived', 'amount', 'comment','donor','donor__lastname','donor__firstname','donor__email')
	donations = fixorder(donations, orderdict, sort, order)
	fulllist = request.user.has_perm('tracker.view_full_list') and 'full' in request.GET
	paginator = Paginator(donations,50)
	if fulllist:
		pageinfo = { 'paginator' : paginator, 'has_previous' : False, 'has_next' : False }
		page = 0
	else:
		try:
			pageinfo = paginator.page(page)
		except PageIsNotAnInteger:
			pageinfo = paginator.page(1)
		except EmptyPage:
			pageinfo = paginator.page(paginator.num_pages)
		donations = pageinfo.object_list
	agg = Donation.objects.filter(amount__gt="0.0").aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
	return tracker_response(request, 'tracker/donationindex.html', { 'donations' : donations, 'pageinfo' :  pageinfo, 'agg' : agg, 'fulllist' : fulllist, 'sort' : sort, 'order' : order, 'page' : page })

def donation(request,id):
	try:
		donation = Donation.objects.get(pk=id)
		donor = donation.donor
		choicebids = ChoiceBid.objects.filter(donation=id).select_related('option','option__choice','option__choice__speedrun')#values('amount', 'option', 'option__name', 'option__choice', 'option__choice__name', 'option__choice__speedrun', 'option__choice__speedrun__name')
		challengebids = ChallengeBid.objects.filter(donation=id).values('amount', 'challenge', 'challenge__name', 'challenge__goal', 'challenge__speedrun', 'challenge__speedrun__name')
		return tracker_response(request, 'tracker/donation.html', { 'donation' : donation, 'donor' : donor, 'choicebids' : choicebids, 'challengebids' : challengebids })
	except Donation.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def runindex(request):
	runs = SpeedRun.objects.all().annotate(choices=Sum('choice'), challenges=Sum('challenge'))
	return tracker_response(request, 'tracker/runindex.html', { 'runs' : runs })

def run(request,id):
	try:
		run = SpeedRun.objects.get(pk=id)
		challenges = Challenge.objects.filter(speedrun=id).annotate(amount=Sum('challengebid__amount'), count=Count('challengebid'))
		choices = Choice.objects.filter(speedrun=id).values('id', 'name', 'choiceoption', 'choiceoption__name',).annotate(amount=Sum('choiceoption__choicebid__amount'), count=Count('choiceoption__choicebid')).order_by('name', '-amount')
		return tracker_response(request, 'tracker/run.html', { 'run' : run, 'challenges' : challenges, 'choices' : choices })
	except SpeedRun.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def prizeindex(request):
	# there has to be a better way to do this
	prizes1 = Prize.objects.values('id', 'name', 'sortkey', 'image', 'minimumbid', 'startgame', 'startgame__name', 'endgame', 'endgame__name', 'winner', 'winner__firstname', 'winner__lastname', 'winner__email')
	prizes2 = Prize.objects.values('id', 'name', 'sortkey', 'image', 'minimumbid').filter(winner__isnull=True,startgame__isnull=True)
	prizes3 = Prize.objects.values('id', 'name', 'sortkey', 'image', 'minimumbid', 'startgame', 'startgame__name', 'endgame', 'endgame__name').filter(winner__isnull=True)
	prizes4 = Prize.objects.values('id', 'name', 'sortkey', 'image', 'minimumbid', 'winner', 'winner__firstname', 'winner__lastname', 'winner__email').filter(startgame__isnull=True)
	prizes = list(prizes1) + list(prizes2) + list(prizes3) + list(prizes4)
	prizes.sort(key=lambda x: x['sortKey'])
	return tracker_response(request, 'tracker/prizeindex.html', { 'prizes' : prizes })

def prize(request,id):
	try:
		prize = Prize.objects.filter(id=id).values('name', 'image', 'description', 'minimumbid', 'startgame', 'endgame', 'winner')[0]
		games = None
		winner = None
		if prize['startgame']:
			startgame = SpeedRun.objects.get(pk=prize['startgame'])
			endgame = SpeedRun.objects.get(pk=prize['endgame'])
			games = SpeedRun.objects.filter(sortkey__gte=startgame.sortkey,sortkey__lte=endgame.sortkey)
		if prize['winner']:
			winner = Donor.objects.get(pk=prize['winner'])
		return tracker_response(request, 'tracker/prize.html', { 'prize' : prize, 'games' : games, 'winner' : winner })
	except Prize.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

@never_cache
def chipin_action(request):
	action = request.GET.get('action', 'merge')
	eventname = request.GET.get('event', '')
	if not request.user.has_perm('can_sync_chipin'):
		return tracker_response(request, template='404.html', status=404)
	try:
		event = Event.objects.get(short=eventname)
		id = event.chipinid
	except Event.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)
	if not id:
		raise chipin.Error('Not set up for Event %s' % database)
	if not chipin.login(settings.CHIPIN_LOGIN, settings.CHIPIN_PASSWORD):
		raise chipin.Error('Login failed, check settings')
	if action == 'merge':
		return HttpResponse(chipin.merge(event, id), mimetype='text/plain')
	raise chipin.Error('Unrecognized chipin action')
