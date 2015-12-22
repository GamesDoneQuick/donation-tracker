import csv

from django.core.urlresolvers import reverse
from django.contrib.auth import *
from django.contrib.auth.models import *
from django.utils.safestring import mark_safe
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.db import transaction

import post_office.mail
import post_office.models

import settings

from tracker.models import *
from tracker import viewutil
from tracker import auth
from tracker import mailutil

AuthUser = get_user_model()

_targetColumns = ['name', 'username', 'email', 'position', ]

class DryRunException(Exception):
    pass

class VolunteerInfo:
    def __init__(self, firstname, lastname, username, email, is_head):
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        self.email = email
        self.isHead = is_head

        
def parse_header_row(row):
    mapping = {}
    columnIndex = 0
    for column in row:
        column = column.strip().lower()
        if column in _targetColumns:
            mapping[column] = columnIndex
        columnIndex += 1
    return mapping
    
    
def parse_volunteer_row(row, mapping):
    position = row[mapping['position']].strip().lower()
    if 'head' in position:
        isHead = True
    else:
        isHead = False
    firstname, space, lastname = row[mapping['name']].strip().partition(' ')
    username = row[mapping['username']].strip()
    email = row[mapping['email']].strip()
    return VolunteerInfo(firstname=firstname, lastname=lastname, username=username, email=email, is_head=isHead)
    

def parse_volunteer_info_file(csvFilename):
    csvFile = open(csvFilename, 'r')
    csvReader = csv.reader(csvFile)
    header = True
    volunteers = []
    mapping = {}
    for row in csvReader:
        if header:
            header = False
            mapping = parse_header_row(row)
        else:
            volunteers.append(parse_volunteer_row(row, mapping))
    csvFile.close()
    return volunteers


def send_volunteer_mail(domain, event, volunteers, template, sender=None, token_generator=default_token_generator, verbosity=0, dry_run=False):
    if not sender:
        sender = viewutil.get_default_email_from_user()
    adminGroup, created = Group.objects.get_or_create(name='Bid Admin')
    trackerGroup, created = Group.objects.get_or_create(name='Bid Tracker')
    for volunteer in volunteers:
        try:
            with transaction.atomic():
                user,created = AuthUser.objects.get_or_create(email=volunteer.email, defaults=dict(username=volunteer.username, first_name=volunteer.firstname, last_name=volunteer.lastname, is_active=False))
                user.is_staff = True
                if volunteer.isHead:
                    user.groups.add(adminGroup)
                    user.groups.remove(trackerGroup)
                else:
                    user.groups.remove(adminGroup)
                    user.groups.add(trackerGroup)
                user.save()
            
                if verbosity > 0:
                    if created:
                        print("Created user {0} with email {1}".format(volunteer.username, volunteer.email))
                    else:
                        print("Found existing user {0} with email {1}".format(volunteer.username, volunteer.email))
                
                context = dict(
                    event=event,
                    is_head=volunteer.isHead,
                    password_reset_url=domain + reverse('password_reset'),
                    registration_url=domain + reverse('register'))
                
                if verbosity > 0:
                    print("Sending email to {0}, active = {1}, head = {2}".format(volunteer.username, user.is_active, volunteer.isHead))
                
                if not dry_run:
                    auth.send_registration_mail(domain, user, template, sender, token_generator, extra_context=context)
                else:
                    raise DryRunException
        except DryRunException:
            pass # do not commit anything to the db in dry run mode
