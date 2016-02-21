import itertools

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

import tracker.commandutil as commandutil
import tracker.auth as authutil

AuthUser = get_user_model()

def collect_users(groups, excluded, users):
    excluded = map(lambda exclude: Group.objects.get(name=exclude), excluded)
    groups = map(lambda group: Group.objects.get(name=group), groups)
    if excluded and not groups:
        groups = Group.objects.all()
    users = map(lambda uid: authutil.get_user(uid), users)
    return set(AuthUser.objects.filter(groups__in=groups).exclude(groups__in=excluded)) | set(users)


class Command(commandutil.TrackerCommand):
    help = "Revokes admin access for the specified groups"
    
    def add_arguments(self, parser):
        parser.add_argument('-x', '--exclude-groups', nargs='+', default=[], help="Specify a set of groups to *not* revoke admin access from.")
        parser.add_argument('-g', '--groups', nargs='+', default=[], help="Specify a set of groups to revoke admin access from.")
        parser.add_argument('-u', '--users', nargs='+', default=[], help="Specify a set of users to revoke admin access from.")
        parser.add_argument('-l', '--list', action='store_true', help="List the set of users access would be revoked from, but do not perform any changes.")
    
    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        
        for user in collect_users(options['groups'], options['exclude_groups'], options['users']):
            if user.is_staff:
                if not options['list']:
                    self.message("Revoking staff access from {0}".format(user.username))
                    user.is_staff = False
                    user.save()
                else:
                    self.message(user.username)
