from django.contrib import admin
import tracker.models

class ChallengeAdmin(admin.ModelAdmin):
	list_display = ('speedrun', 'name', 'goal', 'description', 'state')
	list_editable = ('name', 'goal', 'state')

class ChallengeBidAdmin(admin.ModelAdmin):
	list_display = ('challenge', 'donation', 'amount')

class ChoiceAdmin(admin.ModelAdmin):
	pass

class ChoiceBidAdmin(admin.ModelAdmin):
	list_display = ('option', 'donation', 'amount')

class ChoiceOptionAdmin(admin.ModelAdmin):
	list_display = ('choice', 'name')

class DonationAdmin(admin.ModelAdmin):
	list_display = ('donor', 'amount', 'timereceived', 'event', 'domain', 'bidstate', 'readstate', 'commentstate',)

class DonorAdmin(admin.ModelAdmin):
	pass

class EventAdmin(admin.ModelAdmin):
	pass

class PrizeAdmin(admin.ModelAdmin):
	pass

class SpeedRunAdmin(admin.ModelAdmin):
	pass

admin.site.register(tracker.models.Challenge, ChallengeAdmin)
admin.site.register(tracker.models.ChallengeBid, ChallengeBidAdmin)
admin.site.register(tracker.models.Choice, ChoiceAdmin)
admin.site.register(tracker.models.ChoiceBid, ChoiceBidAdmin)
admin.site.register(tracker.models.ChoiceOption, ChoiceOptionAdmin)
admin.site.register(tracker.models.Donation, DonationAdmin)
admin.site.register(tracker.models.Donor, DonorAdmin)
admin.site.register(tracker.models.Event)
admin.site.register(tracker.models.Prize, PrizeAdmin)
admin.site.register(tracker.models.SpeedRun, SpeedRunAdmin)
admin.site.register(tracker.models.UserProfile)
