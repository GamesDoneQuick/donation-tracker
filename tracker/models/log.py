from django.contrib.auth.models import User
from django.db import models


class Log(models.Model):
    timestamp = models.DateTimeField(
        auto_now_add=True, verbose_name='Timestamp', db_index=True
    )
    category = models.CharField(
        max_length=64, default='other', blank=False, null=False, verbose_name='Category'
    )
    message = models.TextField(blank=True, null=False, verbose_name='Message')
    event = models.ForeignKey('Event', blank=True, null=True, on_delete=models.PROTECT)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.PROTECT)

    class Meta:
        app_label = 'tracker'
        verbose_name = 'Log'
        ordering = ['-timestamp']

    def __str__(self):
        result = str(self.timestamp)
        if self.event:
            result += ' (' + self.event.short + ')'
        result += ' -- ' + self.category
        if self.message:
            m = self.message
            if len(m) > 18:
                m = m[:15] + '...'
            result += ': ' + m
        return result
