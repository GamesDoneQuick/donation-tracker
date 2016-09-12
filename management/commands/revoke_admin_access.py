import itertools

from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model

import tracker.commandutil as commandutil
from tracker.management.auth import collect_group_users

AuthUser = get_user_model()


class Command(commandutil.TrackerCommand):
    help = "Revokes admin access for the specified groups"
    
    def add_arguments(self, parser):
        parser.add_argument('-x', '--exclude-groups', nargs='+', default=[], help="Specify a set of groups to *not* revoke admin access from.")
        parser.add_argument('-g', '--groups', nargs='+', default=[], help="Specify a set of groups to revoke admin access from.")
        parser.add_argument('-u', '--users', nargs='+', default=[], help="Specify a set of users to revoke admin access from.")
        parser.add_argument('-l', '--list', action='store_true', help="List the set of users access would be revoked from, but do not perform any changes.")
    
    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        
        users = set(map(lambda uid: authutil.get_user(uid), options['users']))
        users |= set(collect_group_users(options['groups'], options['exclude_groups']))
        
        for user in users:
            if user.is_staff:
                if not options['list']:
                    self.message("Revoking staff access from {0}".format(user.username))
                    user.is_staff = False
                    user.save()
                else:
                    self.message(user.username)
