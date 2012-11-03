import django

from django import shortcuts
from django.shortcuts import render,render_to_response

from django.db import connection
from django.db.models import Count,Sum,Max,Avg,Q
from django.db.utils import ConnectionDoesNotExist,IntegrityError

from django.core import serializers,paginator
from django.core.paginator import Paginator
from django.core.cache import cache
from django.core.exceptions import FieldError,ObjectDoesNotExist

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
import logutil as log

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
		'bidtracker' : bidtracker,
		'djangoversion' : dv(),
		'pythonversion' : pv(),
		'user' : request.user,
		'profile' : profile,
		'prepend' : prepend,
		'next' : request.REQUEST.get('next', request.path),
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
	except Exception,e:
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

modelmap = {
	'challenge'    : Challenge,
	'challengebid' : ChallengeBid,
	'choice'       : Choice,
	'choicebid'    : ChoiceBid,
	'choiceoption' : ChoiceOption,
	'donation'     : Donation,
	'donor'        : Donor,
	'event'        : Event,
	'prize'        : Prize,
	'run'          : SpeedRun,
	}
fkmap = { 'winner': 'donor', 'speedrun': 'run', 'startrun': 'run', 'endrun': 'run', 'option': 'choiceoption' }

@never_cache
def search(request):
	if not request.user.has_perm('tracker.can_search'):
		return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
	try:
		searchtype = request.GET['type']
		qfilter = {}
		general = {
			'challenge'    : [ 'speedrun', 'name', 'description' ],
			'challengebid' : [ 'challenge', 'donation' ],
			'choice'       : [ 'speedrun', 'name', 'description' ],
			'choicebid'    : [ 'option', 'donation' ],
			'choiceoption' : [ 'choice', 'name' ],
			'donation'     : [ 'donor', 'comment' ],
			'donor'        : [ 'email', 'alias', 'firstname', 'lastname' ],
			'event'        : [ 'short', 'name' ],
			'prize'        : [ 'name', 'description', 'winner' ],
			'run'          : [ 'name', 'runners', 'description' ]
			}
		specific = {
			'challenge': {
				'event'       : 'speedrun__event',
				'eventname'   : 'speedrun__event__short',
				'run'         : 'speedrun',
				'runname'     : 'speedrun__name__icontains',
				'name'        : 'name__icontains',
				'description' : 'description__icontains',
				'state'       : 'state__iequals',
				'pin'         : 'pin'
			},
			'challengebid': {
				'event'         : 'donation__event',
				'eventname'     : 'donation__event__short',
				'run'           : 'challenge__speedrun',
				'runname'       : 'challenge__speedrun__name__icontains',
				'challenge'     : 'challenge',
				'challengename' : 'challenge__name__icontains',
				'donation'      : 'donation',
				'donor'         : 'donation__donor',
				'amount'        : 'amount',
				'amount_lte'    : 'amount__lte',
				'amount_gte'    : 'amount__gte'
			},
			'choice': {
				'event'      : 'speedrun__event',
				'eventname'  : 'speedrun__event__short',
				'run'        : 'speedrun',
				'runname'    : 'speedrun__name__icontains',
				'name'       : 'name__icontains',
				'state'      : 'state',
				'pin'        : 'pin'
			},
			'choiceoption': {
				'event'      : 'choice__speedrun__event',
				'eventname'  : 'choice__speedrun__event__short',
				'run'        : 'choice__speedrun',
				'runname'    : 'choice__speedrun__name__icontains',
				'choice'     : 'choice',
				'choicename' : 'choice__name__icontains',
				'name'       : 'name__icontains'
			},
			'choicebid': {
				'event'      : 'donation__event',
				'eventname'  : 'donation__event__short',
				'run'        : 'option__choice__speedrun',
				'runname'    : 'option__choice__speedrun__name__icontains',
				'choice'     : 'option__choice',
				'choicename' : 'option__choice__name__icontains',
				'option'     : 'option',
				'optionname' : 'option__name__icontains',
				'donation'   : 'donation',
				'donor'      : 'donation__donor',
				'amount'     : 'amount',
				'amount_lte' : 'amount__lte',
				'amount_gte' : 'amount__gte'
			},
			'donation': {
				'event'        : 'event',
				'eventname'    : 'event__short',
				'donor'        : 'donor',
				'domain'       : 'domain',
				'bidstate'     : 'bidstate',
				'commentstate' : 'commentstate',
				'readstate'    : 'readstate',
				'amount'       : 'amount',
				'amount_lte'   : 'amount__lte',
				'amount_gte'   : 'amount__gte',
				'time_lte'     : 'time__lte',
				'time_gte'     : 'time__gte',
				'comment'      : 'comment__icontains'
			},
			'donor': {
				'event'      : 'donation__event',
				'eventname'  : 'donation__event__short',
				'firstname'  : 'firstname__icontains',
				'lastname'   : 'lastname__icontains',
				'alias'      : 'alias__icontains',
				'email'      : 'email__icontains',
			},
			'event': {
			# no params
			},
			'prize': {
				'event'       : 'event',
				'eventname'   : 'event__short',
				'name'        : 'name__icontains',
				'description' : 'description__icontains',
				'winner'      : 'winner',
				'pin'         : 'pin',
				'provided'    : 'provided__icontains',
			},
			'run': {
				'event'       : 'event',
				'eventname'   : 'event__short',
				'name'        : 'name__icontains',
				'runner'      : 'runners__icontains',
				'description' : 'description__icontains',
			},
		}
		related = {
			'challenge'    : [ 'speedrun' ],
			'choice'       : [ 'speedrun' ],
			'choiceoption' : [ 'choice', 'choice__speedrun' ],
			'donation'     : [ 'donor' ],
		}
		defer = {
			'challenge'    : [ 'speedrun__description', 'speedrun__endtime', 'speedrun__starttime', 'speedrun__runners', 'speedrun__sortkey', ],
			'choice'       : [ 'speedrun__description', 'speedrun__endtime', 'speedrun__starttime', 'speedrun__runners', 'speedrun__sortkey', ],
			'choiceoption' : [ 'choice__speedrun__description', 'choice__speedrun__endtime', 'choice__speedrun__starttime', 'choice__speedrun__runners', 'choice__speedrun__sortkey', 'choice__description', 'choice__pin', 'choice__state', ],
		}
		annotations = {
			'challenge'    : { 'total': Sum('bids__amount'), 'bidcount': Count('bids') },
			'choice'       : { 'total': Sum('option__bids__amount'), 'bidcount': Count('option__bids') },
			'choiceoption' : { 'total': Sum('bids__amount'), 'bidcount': Count('bids') },
			'donor'        : { 'total': Sum('donation__amount'), 'count': Count('donation'), 'max': Max('donation__amount'), 'avg': Avg('donation__amount') },
		}
		qs = modelmap[searchtype].objects.annotate(**annotations.get(searchtype,{}))
		if 'id' in request.GET:
			qs = qs.filter(id=request.GET['id'])
		elif 'q' in request.GET:
			def recurse(key):
				tail = key.split('__')[-1]
				ftail = fkmap.get(tail,tail)
				if ftail in general or tail in fkmap:
					ret = []
					for key in general[ftail]:
						for k in recurse(key):
							ret.append(tail + '__' + k)
					return ret
				return [key]
			fields = set()
			for key in general[searchtype]:
				fields |= set(recurse(key))
			fields = list(fields)
			qf = Q(**{fields[0] + '__icontains': request.GET['q'] })
			for q in fields[1:]:
				qf |= Q(**{q + '__icontains': request.GET['q']})
			qs = qs.filter(qf)
		for key in specific[searchtype]:
			if key in request.GET:
				qfilter[specific[searchtype][key]] = request.GET[key]
		if qfilter:
			qs = qs.filter(**qfilter)
		if searchtype in related:
			qs = qs.select_related(*related[searchtype])
		if searchtype in defer:
			qs = qs.defer(*defer[searchtype])
		json = simplejson.loads(serializers.serialize('json', qs, ensure_ascii=False))
		objs = dict(map(lambda o: (o.id,o), qs))
		for o in json:
			for a in annotations.get(searchtype,{}):
				o['fields'][a] = unicode(getattr(objs[int(o['pk'])],a))
			for r in related.get(searchtype,[]):
				jo = objs[int(o['pk'])]
				ro = jo
				for f in r.split('__'):
					ro = getattr(ro,f)
				for f in ro.__dict__:
					if f[0] == '_' or f.endswith('id') or f in defer.get(searchtype,[]): continue
					v = unicode(getattr(ro,f))
					o['fields'][r + '__' + f] = v
		resp = HttpResponse(simplejson.dumps(json,ensure_ascii=False),content_type='application/json;charset=utf-8')
		if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
			return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
		return resp
	except KeyError, e:
		return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed search parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except FieldError, e:
		return HttpResponse(simplejson.dumps({'error': 'Field Error, malformed search parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

@never_cache
def add(request):
	try:
		addtype = request.POST['type']
		if not request.user.has_perm('tracker.add_' + addtype):
			return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
		Model = modelmap[addtype]
		newobj = Model()
		for k,v in request.POST.items():
			if k in ('type','id'): continue
			if v == 'None':
				v = None
			elif fkmap.get(k,k) in modelmap:
				v = modelmap[fkmap.get(k,k)].objects.get(id=v)
			setattr(newobj,k,v)
		newobj.full_clean()
		newobj.save()
		log.addition(request, newobj)
		resp = HttpResponse(serializers.serialize('json', Model.objects.filter(id=newobj.id), ensure_ascii=False),content_type='application/json;charset=utf-8')
		if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
			return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
		return resp
	except IntegrityError, e:
		return HttpResponse(simplejson.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except ValidationError, e:
		return HttpResponse(simplejson.dumps({'error': u'Validation error', 'fields': e.message_dict}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except KeyError, e:
		return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed add parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except FieldError, e:
		return HttpResponse(simplejson.dumps({'error': 'Field Error, malformed add parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except ValueError, e:
		return HttpResponse(simplejson.dumps({'error': u'Value Error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

@never_cache
def delete(request):
	try:
		deltype = request.POST['type']
		if not request.user.has_perm('tracker.delete_' + deltype):
			return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
		obj = modelmap[deltype].objects.get(pk=request.POST['id'])
		log.deletion(obj)
		obj.delete
		return HttpResponse(simplejson.dumps({'result': u'Object %s of type %s deleted' % (request.POST['id'],request.POST['type'])}, ensure_ascii=False), content_type='application/json;charset=utf-8')
	except IntegrityError, e:
		return HttpResponse(simplejson.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except ValidationError, e:
		return HttpResponse(simplejson.dumps({'error': u'Validation error', 'fields': e.message_dict}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except KeyError, e:
		return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed delete parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except ObjectDoesNotExist, e:
		return HttpResponse(simplejson.dumps({'error': 'Object does not exist'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

@never_cache
def edit(request):
	try:
		edittype = request.POST['type']
		if not request.user.has_perm('tracker.change_' + edittype):
			return HttpResponse('Access denied',status=403,content_type='text/plain;charset=utf-8')
		Model = modelmap[edittype]
		obj = Model.objects.get(pk=request.POST['id'])
		changed = []
		for k,v in request.POST.items():
			if k in ('type','id'): continue
			if v == 'None':
				v = None
			elif fkmap.get(k,k) in modelmap:
				v = modelmap[fkmap.get(k,k)].objects.get(id=v)
			if unicode(getattr(obj,k)) != unicode(v):
				changed.append(k)
			setattr(obj,k,v)
		obj.full_clean()
		obj.save()
		if changed:
			log.change(request,obj,u'Changed field%s %s.' % (len(changed) > 1 and 's' or '', ', '.join(changed)))
		resp = HttpResponse(serializers.serialize('json', Model.objects.filter(id=obj.id), ensure_ascii=False),content_type='application/json;charset=utf-8')
		if 'queries' in request.GET and request.user.has_perm('tracker.view_queries'):
			return HttpResponse(simplejson.dumps(connection.queries, ensure_ascii=False, indent=1),content_type='application/json;charset=utf-8')
		return resp
	except IntegrityError, e:
		return HttpResponse(simplejson.dumps({'error': u'Integrity error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except ValidationError, e:
		return HttpResponse(simplejson.dumps({'error': u'Validation error', 'fields': e.message_dict}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except KeyError, e:
		return HttpResponse(simplejson.dumps({'error': 'Key Error, malformed edit parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except FieldError, e:
		return HttpResponse(simplejson.dumps({'error': 'Field Error, malformed edit parameters'}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')
	except ValueError, e:
		return HttpResponse(simplejson.dumps({'error': u'Value Error: %s' % e}, ensure_ascii=False), status=400, content_type='application/json;charset=utf-8')

def challengeindex(request):
	challenges = Challenge.objects.select_related('speedrun').annotate(amount=Sum('bids__amount'), count=Count('bids'))
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
	except Challenge.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def choiceindex(request):
	choices = Choice.objects.select_related('speedrun').extra(select={'optionid': 'tracker_choiceoption.id', 'optionname': 'tracker_choiceoption.name'}).annotate(amount=Sum('option__bids__amount'), count=Count('option__bids')).order_by('speedrun__sortkey','name','-amount','option__name')
	agg = ChoiceBid.objects.aggregate(amount=Sum('amount'), count=Count('amount'))
	return tracker_response(request, 'tracker/choiceindex.html', { 'choices' : choices, 'agg' : agg })

def choice(request,id):
	try:
		choice = Choice.objects.get(pk=id)
		choicebids = ChoiceBid.objects.filter(option__choice=id).select_related('option', 'donation', 'donation__donor').order_by('-donation__timereceived')
		options = ChoiceOption.objects.filter(choice=id).annotate(amount=Sum('bids__amount'), count=Count('bids__amount')).order_by('-amount')
		agg = ChoiceBid.objects.filter(option__choice=id).aggregate(amount=Sum('amount'), count=Count('amount'))
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
		agg = ChoiceBid.objects.filter(option=id).aggregate(amount=Sum('amount'))
		bids = ChoiceBid.objects.filter(option=id).select_related('donation','donation__donor')
		bids = fixorder(bids, orderdict, sort, order)
		comments = 'comments' in request.GET
		return tracker_response(request, 'tracker/choiceoption.html', { 'choiceoption' : choiceoption, 'bids' : bids, 'comments' : comments, 'agg' : agg })
	except ChoiceOption.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def choicebidadd(request,id):
	return index(request)

def donorindex(request):
	orderdict = {
		'name'  : ('lastname', 'firstname'),
		'total' : ('amount',   ),
		'max'   : ('max',      ),
		'avg'   : ('avg',      )
	}
	page = request.GET.get('page', 1)
	sort = request.GET.get('sort', 'name')
	if sort not in orderdict:
		sort = 'name'
	try:
		order = int(request.GET.get('order', 1))
	except ValueError:
		order = 1
	donors = Donor.objects.filter(lastname__isnull=False).annotate(amount=Sum('donation__amount'), count=Count('donation__amount'), max=Max('donation__amount'), avg=Avg('donation__amount')).order_by(*orderdict[sort])
	if order < 0:
		donors = donors.reverse()
	fulllist = request.user.has_perm('tracker.view_full_list') and page == 'full'
	pages = Paginator(donors,50)
	if fulllist:
		pageinfo = { 'pages' : pages, 'has_previous' : False, 'has_next' : False, 'paginator.num_pages' : pages.num_pages }
		page = 0
	else:
		try:
			pageinfo = pages.page(page)
		except paginator.PageNotAnInteger:
			pageinfo = pages.page(1)
		except paginator.EmptyPage:
			pageinfo = pages.page(pages.num_pages)
			page = pages.num_pages
		donors = pageinfo.object_list
	agg = Donation.objects.aggregate(count=Count('amount'))
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
		'name'   : ('donor__lastname', 'donor__firstname'),
		'amount' : ('amount', ),
		'time'   : ('timereceived', ),
	}
	page = request.GET.get('page', 1)
	sort = request.GET.get('sort', 'time')
	if sort not in orderdict:
		sort = 'time'
	try:
		order = int(request.GET.get('order', -1))
	except ValueError:
		order = -1
	donations = Donation.objects.select_related('donor').order_by(*orderdict[sort])
	if order < 0:
		donations = donations.reverse()
	fulllist = request.user.has_perm('tracker.view_full_list') and page == 'full'
	pages = Paginator(donations,50)
	if fulllist:
		pageinfo = { 'paginator' : pages, 'has_previous' : False, 'has_next' : False, 'paginator.num_pages' : pages.num_pages }
		page = 0
	else:
		try:
			pageinfo = pages.page(page)
		except paginator.PageNotAnInteger:
			pageinfo = pages.page(1)
		except paginator.EmptyPage:
			pageinfo = pages.page(paginator.num_pages)
			page = pages.num_pages
		donations = pageinfo.object_list
	agg = Donation.objects.filter(amount__gt="0.0").aggregate(amount=Sum('amount'), count=Count('amount'), max=Max('amount'), avg=Avg('amount'))
	return tracker_response(request, 'tracker/donationindex.html', { 'donations' : donations, 'pageinfo' :  pageinfo, 'page' : page, 'fulllist' : fulllist, 'agg' : agg, 'sort' : sort, 'order' : order })

def donation(request,id):
	try:
		donation = Donation.objects.get(pk=id)
		donor = donation.donor
		choicebids = ChoiceBid.objects.filter(donation=id).select_related('option','option__choice','option__choice__speedrun')
		challengebids = ChallengeBid.objects.filter(donation=id).select_related('challenge', 'challenge__speedrun')
		return tracker_response(request, 'tracker/donation.html', { 'donation' : donation, 'donor' : donor, 'choicebids' : choicebids, 'challengebids' : challengebids })
	except Donation.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def runindex(request):
	runs = SpeedRun.objects.all().annotate(choices=Sum('choice'), challenges=Sum('challenge'))
	return tracker_response(request, 'tracker/runindex.html', { 'runs' : runs })

def run(request,id):
	try:
		run = SpeedRun.objects.get(pk=id)
		challenges = Challenge.objects.filter(speedrun=id).annotate(amount=Sum('bids__amount'), count=Count('bids'))
		choices = Choice.objects.filter(speedrun=id).extra(select={'optionid': 'tracker_choiceoption.id', 'optionname': 'tracker_choiceoption.name'}).annotate(amount=Sum('option__bids__amount'), count=Count('option__bids')).order_by('speedrun__sortkey','name','-amount','option__name')
		return tracker_response(request, 'tracker/run.html', { 'run' : run, 'challenges' : challenges, 'choices' : choices })
	except SpeedRun.DoesNotExist:
		return tracker_response(request, template='tracker/badobject.html', status=404)

def prizeindex(request):
	prizes = Prize.objects.select_related('startrun','endrun','winner')
	return tracker_response(request, 'tracker/prizeindex.html', { 'prizes' : prizes })

def prize(request,id):
	try:
		prize = Prize.objects.get(pk=id)
		games = None
		winner = None
		if prize.startrun:
			games = SpeedRun.objects.filter(sortkey__gte=SpeedRun.objects.get(pk=prize.startrun.id).sortkey,sortkey__lte=SpeedRun.objects.get(pk=prize.endrun.id).sortkey)
		if prize.winner:
			winner = Donor.objects.get(pk=prize.winner.id)
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
