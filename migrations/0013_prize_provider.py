# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import collections
import re
import itertools

from django.db import migrations, models
from django.conf import settings


def collect_prize_contributor_names(Prize, AuthUser):
    contributorNames = {}
    for prize in Prize.objects.all():
        if prize.provideremail:
            if prize.provideremail not in contributorNames.keys():
                contributorNames[prize.provideremail] = collections.Counter()
            if prize.provided:
                contributorNames[prize.provideremail][prize.provided.strip()] += 1
    return contributorNames


def guess_user_id(AuthUser, contributorEmail, contributorNameCounter):
    # user email is a reasonable default in the presence of no other alternative
    userId = contributorEmail

    potentialTags = []

    for name,count in contributorNameCounter.items():
        potentialTags.append((count,name))

    potentialTags.sort(reverse=True)

    # ensure that if we select a username, it is unique
    for count,tag in potentialTags:
        if not AuthUser.objects.filter(username=tag).exists():
            userId = tag
        break

    return userId


def ensure_existing_users(Prize, AuthUser):
    prizeContribCounts = collect_prize_contributor_names(Prize, AuthUser)

    for contributorEmail,counterDict in prizeContribCounts.items():
        user = None
        users = AuthUser.objects.filter(email=contributorEmail)
        if users.exists():
             user = users[0]
        else:
            users = AuthUser.objects.filter(username=contributorEmail)
            if users.exists():
                user = users[0]
            else:
                # Creaet a new, inactive user as a placeholder
                user = AuthUser()
                user.is_active = False
        userId = guess_user_id(AuthUser, contributorEmail, counterDict)
        if not user.username:
            user.username = userId
        if not user.email:
            user.email = contributorEmail

        user.save()


def populate_prize_contributors(apps, schema_editor):
    Prize = apps.get_model('tracker', 'Prize')
    AuthUser = Prize.provider.field.rel.to

    ensure_existing_users(Prize, AuthUser)

    for prize in Prize.objects.all():
        if prize.provideremail:
            prize.provider = AuthUser.objects.get(email=prize.provideremail)
        elif prize.provided:
            users = AuthUser.objects.filter(username=prize.provided.strip())
            if users.exists():
                prize.provider = users[0]
        prize.save()


def read_back_prize_contributors(apps, schema_editor):
    Prize = apps.get_model('tracker', 'Prize')
    AuthUser = Prize.provider.field.rel.to
    
    for prize in Prize.objects.all():
        if prize.provider:
            if prize.provider.username != prize.provider.email:
                prize.provided = prize.provider.username
            prize.provideremail = prize.provider.email
        prize.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tracker', '0012_speedrun_giantbomb_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='prize',
            name='provider',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.RunPython(populate_prize_contributors, read_back_prize_contributors),
        migrations.RemoveField(
            model_name='prize',
            name='provided',
        ),
        migrations.RemoveField(
            model_name='prize',
            name='provideremail',
        ),
    ]
