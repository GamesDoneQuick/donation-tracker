from django.contrib import admin
import tracker.models

admin.site.register(tracker.models.Challenge)
admin.site.register(tracker.models.ChallengeBid)
admin.site.register(tracker.models.Choice)
admin.site.register(tracker.models.ChoiceBid)
admin.site.register(tracker.models.ChoiceOption)
admin.site.register(tracker.models.Donation)
admin.site.register(tracker.models.Donor)
admin.site.register(tracker.models.Event)
admin.site.register(tracker.models.Prize)
admin.site.register(tracker.models.SpeedRun)
admin.site.register(tracker.models.UserProfile)
