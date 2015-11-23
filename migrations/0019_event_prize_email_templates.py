# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0018_prizewinner_courier_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='prizecontributoremailtemplate',
            field=models.ForeignKey(related_name='event_prizecontributortemplates', default=None, to='post_office.EmailTemplate', blank=True, help_text=b"Email template to use when responding to prize contributor's submission requests", null=True, verbose_name=b'Prize Contributor Accept/Deny Email Template'),
        ),
        migrations.AddField(
            model_name='event',
            name='prizecoordinator',
            field=models.ForeignKey(default=None, to=settings.AUTH_USER_MODEL, blank=True, help_text=b'The person responsible for managing prize acceptance/distribution', null=True, verbose_name=b'Prize Coordinator'),
        ),
        migrations.AddField(
            model_name='event',
            name='prizeshippedemailtemplate',
            field=models.ForeignKey(related_name='event_prizeshippedtemplates', default=None, to='post_office.EmailTemplate', blank=True, help_text=b'Email template to use when the aprize has been shipped to its recipient).', null=True, verbose_name=b'Prize Shipped Email Template'),
        ),
        migrations.AddField(
            model_name='event',
            name='prizewinneracceptemailtemplate',
            field=models.ForeignKey(related_name='event_prizewinneraccepttemplates', default=None, to='post_office.EmailTemplate', blank=True, help_text=b'Email template to use when someone accepts a prize (and thus it needs to be shipped).', null=True, verbose_name=b'Prize Accepted Email Template'),
        ),
        migrations.AddField(
            model_name='event',
            name='prizewinneremailtemplate',
            field=models.ForeignKey(related_name='event_prizewinnertemplates', default=None, to='post_office.EmailTemplate', blank=True, help_text=b'Email template to use when someone wins a prize.', null=True, verbose_name=b'Prize Winner Email Template'),
        ),
    ]
