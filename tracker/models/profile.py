from django.contrib.auth.models import User
from django.db import models


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    prepend = models.CharField('Template Prepend', max_length=64, blank=True)

    class Meta:
        app_label = 'tracker'
        verbose_name = 'User Profile'
        permissions = (
            ('show_queries', 'Can view database queries'),
            ('can_search_for_user', 'Can use User lookup endpoint'),
        )

    def __str__(self):
        return str(self.user)
