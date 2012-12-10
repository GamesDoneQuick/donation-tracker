from django.db import models
from django.db.models import Sum,Max
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

import calendar
from datetime import datetime
from decimal import Decimal

def positive(value):
	if value <  0: raise ValidationError('Value cannot be negative')

def nonzero(value):
	if value == 0: raise ValidationError('Value cannot be zero')

class OldChallenge(models.Model):
	speedRun = models.ForeignKey('OldSpeedRun',db_column='speedRun')
	name = models.CharField(max_length=64)
	goal = models.DecimalField(decimal_places=2,max_digits=20,db_column='goalAmount')
	description = models.TextField(max_length=1024,null=True,blank=True)
	bidState = models.CharField(max_length=255,choices=(('HIDDEN', 'Hidden'), ('OPENED','Opened'), ('CLOSED','Closed')))
	class Meta:
		db_table = 'Challenge'
		unique_together = ('speedRun','name')
	def __unicode__(self):
		return self.speedRun.name + ' -- ' + self.name

class OldChallengeBid(models.Model):
	challenge = models.ForeignKey('OldChallenge',db_column='challenge')
	donation = models.ForeignKey('OldDonation',db_column='donation')
	amount = models.DecimalField(decimal_places=2,max_digits=20)
	class Meta:
		db_table = 'ChallengeBid'
		verbose_name = 'Challenge Bid'
		ordering = [ '-donation__timeReceived' ]
	def __unicode__(self):
		return unicode(self.challenge) + ' -- ' + unicode(self.donation)

class OldChoice(models.Model):
	speedRun = models.ForeignKey('OldSpeedRun',db_column='speedRun')
	name = models.CharField(max_length=64)
	description = models.TextField(max_length=1024,null=True,blank=True)
	bidState = models.CharField(max_length=255,choices=(('HIDDEN', 'Hidden'), ('OPENED','Opened'), ('CLOSED','Closed')))
	class Meta:
		db_table = 'Choice'
		unique_together = ('speedRun', 'name')
	def __unicode__(self):
		return self.speedRun.name + ' -- ' + self.name

class OldChoiceBid(models.Model):
	choiceOption = models.ForeignKey('OldChoiceOption',db_column='choiceOption')
	donation = models.ForeignKey('OldDonation',db_column='donation')
	amount = models.DecimalField(decimal_places=2,max_digits=20)
	class Meta:
		db_table = 'ChoiceBid'
		verbose_name = 'Choice Bid'
		ordering = [ 'choiceOption__choice__speedRun__name', 'choiceOption__choice__name' ]
	def __unicode__(self):
		return unicode(self.choiceOption) + ' (' + unicode(self.donation.donor) + ') (' + unicode(self.amount) + ')'

class OldChoiceOption(models.Model):
	choice = models.ForeignKey('OldChoice',db_column='choice')
	name = models.CharField(max_length=64)
	class Meta:
		db_table = 'ChoiceOption'
		verbose_name = 'Choice Option'
		unique_together = ('choice', 'name')
	def __unicode__(self):
		return unicode(self.choice) + ' -- ' + self.name

class OldDonation(models.Model):
	donor = models.ForeignKey('OldDonor',db_column='donor')
	domain = models.CharField(max_length=255, choices=(('LOCAL', 'Local'), ('CHIPIN', 'ChipIn')))
	domainId = models.CharField(max_length=160,unique=True)
	bidState = models.CharField(max_length=255, choices=(('PENDING', 'Pending'), ('IGNORED', 'Ignored'), ('PROCESSED', 'Processed'), ('FLAGGED', 'Flagged')))
	readState = models.CharField(max_length=255, choices=(('PENDING', 'Pending'), ('IGNORED', 'Ignored'), ('READ', 'Read'), ('FLAGGED', 'Flagged')))
	commentState = models.CharField(max_length=255, choices=(('PENDING', 'Pending'), ('DENIED', 'Denied'), ('APPROVED', 'Approved'), ('FLAGGED', 'Flagged')))
	amount = models.DecimalField(decimal_places=2,max_digits=20)
	timeReceived = models.DateTimeField()
	comment = models.TextField(max_length=4096,null=True,blank=True)
	class Meta:
		db_table = 'Donation'
		permissions = (
			('view_full_list', 'Can view full donation list'),
			('sync_chipin', 'Can start a chipin sync'),
		)
		get_latest_by = 'timeReceived'
		ordering = [ '-timeReceived' ]
	def __unicode__(self):
		return unicode(self.donor) + ' (' + unicode(self.amount) + ') (' + unicode(self.timeReceived) + ')'

class OldDonor(models.Model):
	email = models.EmailField(max_length=128,unique=True)
	alias = models.CharField(max_length=32,unique=True,null=True,blank=True)
	firstName = models.CharField(max_length=32)
	lastName = models.CharField(max_length=32)
	class Meta:
		db_table = 'Donor'
		permissions = (
			('view_usernames', 'Can view full usernames'),
			('view_emails', 'Can view email addresses'),
		)
		ordering = ['lastName', 'firstName', 'email']
	def full(self):
		return unicode(self.email) + ' (' + unicode(self) + ')'
	def __unicode__(self):
		ret = unicode(self.lastName) + ', ' + unicode(self.firstName)
		if self.alias and len(self.alias) > 0:
			ret += ' (' + unicode(self.alias) + ')'
		return ret

class OldPrize(models.Model):
	name = models.CharField(max_length=64,unique=True)
	sortKey = models.IntegerField(db_index=True)
	image = models.URLField(max_length=1024,db_column='imageURL',null=True,blank=True)
	description = models.TextField(max_length=1024,null=True,blank=True)
	minimumBid = models.DecimalField(decimal_places=2,max_digits=20,default=5.0)
	startGame = models.ForeignKey('OldSpeedRun',db_column='startGame',related_name='prizeStart')
	endGame = models.ForeignKey('OldSpeedRun',db_column='endGame',related_name='prizeEnd')
	winner = models.ForeignKey('OldDonor',db_column='winner')
	class Meta:
		db_table = 'Prize'
		ordering = [ 'sortKey', 'name' ]
	def __unicode__(self):
		return unicode(self.name)

class OldSpeedRun(models.Model):
	name = models.CharField(max_length=64,unique=True)
	runners = models.CharField(max_length=1024)
	sortKey = models.IntegerField(db_index=True)
	description = models.TextField(max_length=1024)
	startTime = models.DateTimeField()
	endTime = models.DateTimeField()
	class Meta:
		db_table = 'SpeedRun'
		verbose_name = 'Speed Run'
		ordering = [ 'startTime' ]
	def __unicode__(self):
		return unicode(self.name)

class Event(models.Model):
	short = models.CharField(max_length=64,unique=True)
	name = models.CharField(max_length=128)
	chipinid = models.CharField(max_length=128,unique=True,null=True,blank=True)
	scheduleid = models.CharField(max_length=128,unique=True,null=True,blank=True)
	scheduledatetimefield = models.CharField(max_length=128,blank=True)
	schedulegamefield = models.CharField(max_length=128,blank=True)
	schedulerunnersfield = models.CharField(max_length=128,blank=True)
	scheduleestimatefield = models.CharField(max_length=128,blank=True)
	schedulesetupfield = models.CharField(max_length=128,blank=True)
	schedulecommentatorsfield = models.CharField(max_length=128,blank=True)
	schedulecommentsfield = models.CharField(max_length=128,blank=True)
	date = models.DateField()
	def __unicode__(self):
		return self.name
	def clean(self):
		if self.id and self.id < 1:
			raise ValidationError('Event ID must be positive and non-zero')

class Challenge(models.Model):
	speedrun = models.ForeignKey('SpeedRun',verbose_name='Run')
	name = models.CharField(max_length=64)
	goal = models.DecimalField(decimal_places=2,max_digits=20)
	description = models.TextField(max_length=1024,null=True,blank=True)
	state = models.CharField(max_length=255,choices=(('HIDDEN', 'Hidden'), ('OPENED','Opened'), ('CLOSED','Closed')))
	pin = models.BooleanField()
	class Meta:
		unique_together = ('speedrun','name')
		ordering = [ 'speedrun__sortkey', 'name' ]
	def __unicode__(self):
		return self.speedrun.name + ' -- ' + self.name

class ChallengeBid(models.Model):
	challenge = models.ForeignKey('Challenge',related_name='bids')
	donation = models.ForeignKey('Donation')
	amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero])
	class Meta:
		verbose_name = 'Challenge Bid'
		ordering = [ '-donation__timereceived' ]
	def __unicode__(self):
		return unicode(self.challenge) + ' -- ' + unicode(self.donation)

class Choice(models.Model):
	speedrun = models.ForeignKey('SpeedRun',verbose_name='Run')
	name = models.CharField(max_length=64)
	description = models.TextField(max_length=1024,null=True,blank=True)
	state = models.CharField(max_length=255,choices=(('HIDDEN', 'Hidden'), ('OPENED','Opened'), ('CLOSED','Closed')))
	pin = models.BooleanField()
	class Meta:
		unique_together = ('speedrun', 'name')
	def __unicode__(self):
		return self.speedrun.name + ' -- ' + self.name

class ChoiceBid(models.Model):
	option = models.ForeignKey('ChoiceOption',related_name='bids')
	donation = models.ForeignKey('Donation')
	amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero])
	class Meta:
		verbose_name = 'Choice Bid'
		ordering = [ 'option__choice__speedrun__sortkey', 'option__choice__name' ]
	def __unicode__(self):
		return unicode(self.option) + ' (' + unicode(self.donation.donor) + ') (' + unicode(self.amount) + ')'

class ChoiceOption(models.Model):
	choice = models.ForeignKey('Choice',related_name='option')
	name = models.CharField(max_length=64)
	class Meta:
		verbose_name = 'Choice Option'
		unique_together = ('choice', 'name')
	def __unicode__(self):
		return unicode(self.choice) + ' -- ' + self.name

class Donation(models.Model):
	donor = models.ForeignKey('Donor')
	event = models.ForeignKey('Event')
	domain = models.CharField(max_length=255,default='LOCAL',choices=(('LOCAL', 'Local'), ('CHIPIN', 'ChipIn')))
	domainId = models.CharField(max_length=160,unique=True,editable=False,blank=True)
	bidstate = models.CharField(max_length=255,default='PENDING',choices=(('PENDING', 'Pending'), ('IGNORED', 'Ignored'), ('PROCESSED', 'Processed'), ('FLAGGED', 'Flagged')),verbose_name='Bid State')
	readstate = models.CharField(max_length=255,default='PENDING',choices=(('PENDING', 'Pending'), ('IGNORED', 'Ignored'), ('READ', 'Read'), ('FLAGGED', 'Flagged')),verbose_name='Read State')
	commentstate = models.CharField(max_length=255,default='PENDING',choices=(('PENDING', 'Pending'), ('DENIED', 'Denied'), ('APPROVED', 'Approved'), ('FLAGGED', 'Flagged')),verbose_name='Comment State')
	amount = models.DecimalField(decimal_places=2,max_digits=20,validators=[positive,nonzero])
	timereceived = models.DateTimeField(verbose_name='Time Received')
	comment = models.TextField(blank=True)
	modcomment = models.TextField(blank=True,verbose_name='Moderator Comment')
	class Meta:
		permissions = (
			('view_full_list', 'Can view full donation list'),
			('view_comments', 'Can view all comments'),
		)
		get_latest_by = 'timereceived'
		ordering = [ '-timereceived' ]
	def clean(self):
		super(Donation,self).clean()
		if not self.domainId:
			self.domainId = str(calendar.timegm(self.timereceived.timetuple())) + self.donor.email
	def __unicode__(self):
		return unicode(self.donor) + ' (' + unicode(self.amount) + ') (' + unicode(self.timereceived) + ')'

class Donor(models.Model):
	email = models.EmailField(max_length=128,unique=True)
	alias = models.CharField(max_length=32,unique=True,null=True,blank=True)
	firstname = models.CharField(max_length=32,null=True,blank=True,verbose_name='First Name')
	lastname = models.CharField(max_length=32,verbose_name='Last Name')
	anonymous = models.BooleanField()
	class Meta:
		permissions = (
			('view_usernames', 'Can view full usernames'),
			('view_emails', 'Can view email addresses'),
		)
		ordering = ['lastname', 'firstname', 'email']
	def full(self):
		return unicode(self.email) + ' (' + unicode(self) + ')'
	def __unicode__(self):
		ret = unicode(self.lastname) + ', ' + unicode(self.firstname)
		if self.alias and len(self.alias) > 0:
			ret += ' (' + unicode(self.alias) + ')'
		return ret

class Prize(models.Model):
	name = models.CharField(max_length=64,unique=True)
	category = models.ForeignKey('PrizeCategory',null=True,blank=True)
	sortkey = models.IntegerField(default=0,db_index=True)
	image = models.URLField(max_length=1024,null=True,blank=True)
	description = models.TextField(max_length=1024,null=True,blank=True)
	minimumbid = models.DecimalField(decimal_places=2,max_digits=20,default=5.0,verbose_name='Minimum Bid',validators=[positive,nonzero])
	maximumbid = models.DecimalField(decimal_places=2,max_digits=20,default=5.0,verbose_name='Maximum Bid',validators=[positive,nonzero])
	sumdonations = models.BooleanField(verbose_name='Sum Donations')
	randomdraw = models.BooleanField(default=True,verbose_name='Random Draw')
	event = models.ForeignKey('Event')
	startrun = models.ForeignKey('SpeedRun',related_name='prize_start',null=True,blank=True,verbose_name='Start Run')
	endrun = models.ForeignKey('SpeedRun',related_name='prize_end',null=True,blank=True,verbose_name='End Run')
	starttime = models.DateTimeField(null=True,blank=True,verbose_name='Start Time')
	endtime = models.DateTimeField(null=True,blank=True,verbose_name='End Time')
	winner = models.ForeignKey('Donor',null=True,blank=True)
	pin = models.BooleanField(default=False)
	provided = models.CharField(max_length=64,blank=True,verbose_name='Provided By')
	class Meta:
		ordering = [ 'sortkey', 'name' ]
		unique_together = ( 'category', 'winner', 'event' )
	def __unicode__(self):
		return unicode(self.name)
	def clean(self):
		if (not self.startrun) != (not self.endrun):
			raise ValidationError('Must have both Start Run and End Run set, or neither')
		if (not self.starttime) != (not self.endtime):
			raise ValidationError('Must have both Start Run and End Run set, or neither')
		if self.startrun and self.starttime:
			raise ValidationError('Cannot have both Start/End Run and Start/End Time set')
		if self.maximumbid < self.minimumbid:
			raise ValidationError('Maximum Bid cannot be lower than Minimum Bid')
		if not self.sumdonations and self.maximumbid != self.minimumbid:
			raise ValidationError('Maximum Bid cannot differ from Minimum Bid if Sum Donations is not checked')
	def eligibledonors(self):
		qs = Donation.objects.filter(event=self.event).select_related('donor')
		if self.startrun:
			qs = qs.filter(timereceived__gte=self.startrun.starttime,timereceived__lte=self.endrun.endtime)
		if self.starttime:
			qs = qs.filter(timereceived__gte=self.starttime,timereceived__lte=self.endtime)
		donors = {}
		for d in qs:
			if self.sumdonations:
				donors.setdefault(d.donor, Decimal('0.0'))
				donors[d.donor] += d.amount
			else:
				donors[d.donor] = max(d.amount,donors.get(d.donor,Decimal('0.0')))
		if not donors:
			return []
		elif self.randomdraw:
			def weight(mn,mx,a):
				if a < mn: return 0.0
				if a > mx: return float(mx/mn)
				return float(a/mn)
			return filter(lambda d: d['weight'] >= 1.0,map(lambda d: {'donor':d[0].id,'amount':d[1],'weight':weight(self.minimumbid,self.maximumbid,d[1])}, donors.items()))
		else:
			m = max(donors.items(), key=lambda d: d[1])
			return [{'donor':m[0].id,'amount':m[1],'weight':1.0}]

class PrizeCategory(models.Model):
	name = models.CharField(max_length=64,unique=True)
	class Meta:
		verbose_name = 'Prize Category'
		verbose_name_plural = 'Prize Categories'
	def __unicode__(self):
		return self.name

class SpeedRun(models.Model):
	name = models.CharField(max_length=64)
	runners = models.CharField(max_length=1024)
	sortkey = models.IntegerField(db_index=True,verbose_name='Sort Key')
	description = models.TextField(max_length=1024)
	event = models.ForeignKey('Event')
	starttime = models.DateTimeField(verbose_name='Start Time')
	endtime = models.DateTimeField(verbose_name='End Time')
	class Meta:
		verbose_name = 'Speed Run'
		unique_together = ( 'name','event' )
		ordering = [ 'event__date', 'sortkey', 'starttime' ]
	def __unicode__(self):
		return u'%s (%s)' % (self.name,self.event)

class UserProfile(models.Model):
	user = models.ForeignKey(User, unique=True)
	prepend = models.CharField('Template Prepend', max_length=64,blank=True)
	class Meta:
		verbose_name = 'User Profile'
		permissions = (
			('show_rendertime', 'Can view page render times'),
			('show_queries', 'Can view database queries'),
			('sync_chipin', 'Can start a chipin sync'),
			('sync_schedule', 'Can sync the schedule'),
			('can_search', 'Can use search url'),
		)
	def __unicode__(self):
		return unicode(self.user)
