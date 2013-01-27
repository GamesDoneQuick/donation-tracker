from django.contrib import admin
import tracker.models

class ChallengeAdmin(admin.ModelAdmin):
	list_display = ('speedrun', 'name', 'goal', 'description', 'state')
	list_editable = ('name', 'goal', 'state')
	search_fields = ('name', 'speedrun__name', 'description')

class ChallengeBidAdmin(admin.ModelAdmin):
	list_display = ('challenge', 'donation', 'amount')

class ChoiceAdmin(admin.ModelAdmin):
	search_fields = ('name', 'speedrun__name', 'description');

class ChoiceBidAdmin(admin.ModelAdmin):
	list_display = ('option', 'donation', 'amount')

class ChoiceOptionAdmin(admin.ModelAdmin):
	list_display = ('choice', 'name')
	search_fields = ('name', 'description', 'choice__name', 'choice__speedrun__name')

class DonationAdmin(admin.ModelAdmin):
	list_display = ('donor', 'amount', 'timereceived', 'event', 'domain', 'transactionstate', 'bidstate', 'readstate', 'commentstate',)
	search_fields = ('donor__email', 'donor__alias', 'donor__firstname', 'donor__lastname', 'amount')

class DonorAdmin(admin.ModelAdmin):
	search_fields = ('email', 'alias', 'firstname', 'lastname')

class EventAdmin(admin.ModelAdmin):
	search_fields = ('short', 'name');
	fieldsets = [
		(None, { 'fields': ['short', 'name', 'receivername', 'date'] }),
		('Paypal', {
			'classes': ['collapse'],
			'fields': ['paypalemail', 'usepaypalsandbox']
		}),
		('Google Document', {
			'classes': ['collapse'],
			'fields': ['scheduleid', 'scheduledatetimefield', 'schedulegamefield', 'schedulerunnersfield', 'scheduleestimatefield', 'schedulesetupfield', 'schedulecommentatorsfield', 'schedulecommentsfield']
		}),
	]

class PrizeAdmin(admin.ModelAdmin):
	list_display = ('name', 'category', 'sortkey', 'bidrange', 'games', 'starttime', 'endtime', 'sumdonations', 'randomdraw', 'pin', 'event', 'winner' )
	list_filter = ('event', 'category')
	search_fields = ('name', 'description', 'winner__firstname', 'winner__lastname', 'winner__alais', 'winner__email')
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

class SpeedRunAdmin(admin.ModelAdmin):
	search_fields = ['name', 'description']	

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
