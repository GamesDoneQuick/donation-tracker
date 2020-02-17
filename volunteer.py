import csv

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.urls import reverse

from tracker import auth
from tracker import viewutil

AuthUser = get_user_model()

TARGET_COLUMNS = [
    'name',
    'username',
    'email',
    'position',
]


class DryRunException(Exception):
    pass


class VolunteerInfo:
    def __init__(self, firstname, lastname, username, email, is_head):
        self.firstname = firstname
        self.lastname = lastname
        self.username = username
        self.email = email
        self.is_head = is_head


def parse_header_row(row):
    mapping = {}
    column_index = 0
    for column in row:
        column = column.strip().lower()
        if column in TARGET_COLUMNS:
            mapping[column] = column_index
        column_index += 1
    return mapping


def parse_volunteer_row(row, mapping):
    position = row[mapping['position']].strip().lower()
    is_head = 'head' in position
    firstname, space, lastname = row[mapping['name']].strip().partition(' ')
    username = row[mapping['username']].strip()
    email = row[mapping['email']].strip()
    return VolunteerInfo(
        firstname=firstname,
        lastname=lastname,
        username=username,
        email=email,
        is_head=is_head,
    )


def parse_volunteer_info_file(csv_filename):
    csv_file = open(csv_filename, 'r')
    csv_reader = csv.reader(csv_file)
    header = True
    volunteers = []
    mapping = {}
    for row in csv_reader:
        if header:
            header = False
            mapping = parse_header_row(row)
        else:
            volunteers.append(parse_volunteer_row(row, mapping))
    csv_file.close()
    return volunteers


def send_volunteer_mail(
    domain,
    event,
    volunteers,
    template,
    sender=None,
    token_generator=default_token_generator,
    verbosity=0,
    dry_run=False,
):
    if not sender:
        sender = viewutil.get_default_email_from_user()
    admin_group, created = Group.objects.get_or_create(name='Bid Admin')
    tracker_group, created = Group.objects.get_or_create(name='Bid Tracker')
    for volunteer in volunteers:
        try:
            with transaction.atomic():
                user, created = AuthUser.objects.get_or_create(
                    email__iexact=volunteer.email,
                    defaults=dict(
                        username=volunteer.username,
                        first_name=volunteer.firstname,
                        last_name=volunteer.lastname,
                        email=volunteer.email,
                        is_active=False,
                    ),
                )
                user.is_staff = True
                if volunteer.is_head:
                    user.groups.add(admin_group)
                    user.groups.remove(tracker_group)
                else:
                    user.groups.remove(admin_group)
                    user.groups.add(tracker_group)
                user.save()

                if verbosity > 0:
                    if created:
                        print(
                            'Created user {0} with email {1}'.format(
                                volunteer.username, volunteer.email
                            )
                        )
                    else:
                        print(
                            'Found existing user {0} with email {1}'.format(
                                volunteer.username, volunteer.email
                            )
                        )

                context = dict(
                    event=event,
                    is_head=volunteer.is_head,
                    password_reset_url=domain + reverse('tracker:password_reset'),
                    registration_url=domain + reverse('tracker:register'),
                )

                if verbosity > 0:
                    print(
                        'Sending email to {0}, active = {1}, head = {2}'.format(
                            volunteer.username, user.is_active, volunteer.is_head
                        )
                    )

                if not dry_run:
                    auth.send_registration_mail(
                        domain,
                        user,
                        template,
                        sender,
                        token_generator,
                        extra_context=context,
                    )
                else:
                    raise DryRunException
        except DryRunException:
            pass  # do not commit anything to the db in dry run mode
