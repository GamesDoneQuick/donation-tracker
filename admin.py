from django.contrib import admin
import donations.tracker.models

admin.site.register(donations.tracker.models.Challenge)
admin.site.register(donations.tracker.models.ChallengeBid)
admin.site.register(donations.tracker.models.Choice)
admin.site.register(donations.tracker.models.ChoiceBid)
admin.site.register(donations.tracker.models.ChoiceOption)
admin.site.register(donations.tracker.models.Donation)
admin.site.register(donations.tracker.models.Donor)
admin.site.register(donations.tracker.models.Event)
admin.site.register(donations.tracker.models.Prize)
admin.site.register(donations.tracker.models.SpeedRun)
admin.site.register(donations.tracker.models.UserProfile)
