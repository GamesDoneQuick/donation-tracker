import urllib
import urllib2
import cookielib
import httplib
import time
import pytz
import sys
if sys.version_info >= (2, 6, 0):
	from bs4 import BeautifulSoup
else:
	from BeautifulSoup import BeautifulSoup
from datetime import datetime
from tracker.models import *
from decimal import Decimal

cj = cookielib.CookieJar()

class Error:
	def __init__(self, msg='Unknown'):
		self.msg = msg
	def __unicode__(self):
		return u'Chipin Error: ' + self.msg

def hascookie(jar, name):
	for cookie in jar:
		if cookie.name == name: return True
	return False

def dumpcookies(jar):
	for cookie in jar:
		print cookie.name + '=' + cookie.value

def login(login, password):
	global cj
	params = urllib.urlencode((('loginEmail', login), ('loginPassword', password)))
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	request = urllib2.Request('http://www.chipin.com/loginsubmit')
	request.add_data(params)
	response = opener.open(request)
	cj.extract_cookies(response, request)
	response = opener.open('http://www.chipin.com/dashboard')
	redirect = response.geturl()
	if redirect != 'http://www.chipin.com/dashboard':
		return False
	return True

def parserow(row):
	if not row.find_all: row.find_all = row.findAll # bs3 compatibility
	cells = row.find_all('td')
	ret = {'name': cells[0].string.encode('utf-8').decode('utf-8'), 'email': cells[1].string, 'comment': (cells[3].string or '').encode('utf-8').decode('utf-8'), 'timestamp': cells[4].string[:-3], 'amount': cells[5].string }
	ret['id'] = ret['timestamp'] + ret['email']
	#print ret
	return (ret['id'],ret)

def merge(event, id):
	global cj
	if not hascookie(cj, 'JSESSIONID'):
		raise Error('Not logged in')
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	data = opener.open('http://www.chipin.com/contributors/private/id/' + id)
	new = 0
	updated = 0
	donors = dict(map(lambda d: (d.email,d),Donor.objects.all()))
	donations = dict(map(lambda d: (d.domainId,d),Donation.objects.filter(event=event)))
	table = BeautifulSoup(data.read()).find(id='contributortable')
	if not table.find_all: table.find_all = table.findAll # bs3 compatibility
	#print 'Table Extracted'
	rows = dict(map(parserow,table.find_all('tr')))
	newdonations = []
	for id,row in rows.items():
		if not id in donations:
			new += 1
			#print "New Donation: " + str(row)
			donation = Donation()
			donation.event = event
			donation.timereceived = pytz.utc.localize(datetime.utcfromtimestamp(long(row['timestamp'])))
			if row['email'] not in donors:
				donor = Donor()
				donor.email = row['email']
				try:
					donor.firstname = row['name'].split()[0]
					donor.lastname = ' '.join(row['name'].split()[1:])
				except IndexError: # donor had no name?
					donor.firstname = 'John'
					donor.lastname = 'Doe'
					donor.anonymous = True
				donor.save()
				donors[row['email']] = donor
			else:
				donor = donors[row['email']]
			donation.donor = donor
			donation.domainId = id
			donation.domain = 'CHIPIN'
			donation.comment = row['comment']
			donation.commentstate = 'PENDING'
			donation.amount = Decimal(row['amount'])
			if not donation.comment or donation.amount < Decimal(1):
				donation.readstate = 'IGNORED'
			else:
				donation.readstate = 'PENDING'
			if not donation.comment:
				donation.bidstate = 'IGNORED'
			else:
				donation.bidstate = 'PENDING'
			#donation.save()
			newdonations.append(donation)
		elif not donations[id].comment and row['comment']:
			updated += 1
			#print "Updated Donation: " + str(row)
			donation = donations[id]
			donation.comment = row['comment']
			donation.readstate = 'PENDING'
			donation.commentstate = 'PENDING'
			donation.bidstate = 'PENDING'
			donation.save()
	Donation.objects.bulk_create(newdonations)
	return len(rows),new,updated
