import urllib
import urllib2
import cookielib
import httplib
import HTMLParser as htmllib
import time
import datetime
from donations.tracker.models import *
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
	
class ChipinParser(htmllib.HTMLParser):
	def __init__(self):
		htmllib.HTMLParser.__init__(self)
		self.data = {}
		self.intable = False
		self.inrow = False
		self.incolumn = False
		self.added = False
	def handle_starttag(self, tag, attrs):
		if tag == 'table':
			attrs = dict(attrs)
			if attrs.get('id', '') == 'contributortable':
				self.intable = True
		elif self.inrow and tag == 'td':
			self.incolumn = True
			self.column += 1
		elif self.intable and tag == 'tr':
			self.inrow = True
			self.row = [''] * 8
			self.column = -1
	def handle_endtag(self, tag):
		if tag == 'table':
			self.intable = False
		elif tag == 'td':
			self.incolumn = False
		elif tag == 'tr' and self.inrow:
			self.inrow = False
			name = self.row[0]
			email = self.row[1]
			comment = self.row[3]
			timestamp = self.row[4][:-3]
			amount = self.row[5]
			id = timestamp + email
			self.data[id] = {'name': name, 'email': email, 'comment': comment, 'timestamp': timestamp, 'amount': amount, 'id': id}
			try:
				long(timestamp)
			except ValueError:
				print self.row
				print self.data[id]
				raise
	def handle_data(self, data):
		if self.incolumn:
			self.row[self.column] += data
			self.added = True
			

def merge(event, id):
	global cj
	if not hascookie(cj, 'JSESSIONID'):
		raise Error('Not logged in')
	opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
	r = opener.open('http://www.chipin.com/contributors/private/id/' + id)
	data = r.read()
	new = 0
	updated = 0
	donors = {}
	donations = {}
	for donation in Donation.objects.filter(event=event):
		donations[donation.domainId] = donation
	for donor in Donor.objects.all():
		donors[donor.email] = donor
	print len(donors)
	#data = open("sgdq2012.htm").read()
	parser = ChipinParser()
	parser.feed(data)
	for id,row in parser.data.items():
		if not id in donations:
			new += 1
			print "New Donation: " + str(row)
			donation = Donation()
			donation.event = event
			donation.timereceived = datetime.datetime.utcfromtimestamp(long(row['timestamp']))
			if row['email'] not in donors:
				donor = Donor()
				donor.email = row['email']
				donor.firstname = row['name'].split()[0]
				donor.lastname = ' '.join(row['name'].split()[1:])
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
			donation.save()
		elif not donations[id].comment and row['comment']:
			updated += 1
			print "Updated Donation: " + str(row)
			donation = donations[id]
			donation.comment = row['comment']
			donation.readstate = 'PENDING'
			donation.commentstate = 'PENDING'
			donation.bidstate = 'PENDING'
			donation.save()
	return len(parser.data),new,updated
	