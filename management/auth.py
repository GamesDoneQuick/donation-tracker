from django.apps import apps
from django.contrib.auth.models import Permission, Group as AuthGroup
from django.contrib.auth import get_user_model

AuthUser = get_user_model()


import tracker.auth as authutil

def initialize_default_groups(groups, set_to_default=False, break_on_error=True, verbosity=1):
    """
    (re-)Initialize the set of default auth groups for the tracker
    if `set_to_default` is True, then it will forcibly remove any permissions not
    in the default settings.
    """
    for groupObj in groups:
        initialize_group(groupObj['name'], groupObj['permissions'], set_to_default=set_to_default)


def initialize_group(name, permissions, set_to_default=False, break_on_error=True, verbosity=1):
    group,created = AuthGroup.objects.get_or_create(name=name)
    if not created and set_to_default:
        group.permissions.clear()
        group.save()
    for permission in permissions:
        appName, sep, permName = permission.rpartition('.')
        searchParams = dict(codename=permName)
        if sep:
            searchParams['content_type__app_label'] = appName
        found = Permission.objects.filter(content_type__app_label=appName, codename=permName)
        if not found.exists():
            if error_on_missing:
                raise Exception("Permission {0} was not found".format(permission))
            elif verbosity >= 1:
                print("Permission {0} was not found, skipping".format(permission))
        elif found.count() > 1:
            if break_on_error:
                raise Exception("Duplicate permissions found for {0}".format(permission))
            elif verbosity >= 1:
                print("Duplicate permissions found for {0}, skipping".format(permission))
    	else:
            permObj = found[0]
            if not group.permissions.filter(pk=permObj.pk).exists():
                if verbosity >= 1:
                    print("Adding permission {0} to group {1}".format(permission, name))
                group.permissions.add(permObj)
    group.save()
    return group


def collect_group_users(groups=[], excluded=[]):
    """Collects all users that match the specified groups, and do not match the excluded groups"""
    excluded = map(lambda exclude: AuthGroup.objects.get(name=exclude), excluded)
    groups = map(lambda group: AuthGroup.objects.get(name=group), groups)
    if excluded and not groups:
        groups = AuthGroup.objects.all()
    return AuthUser.objects.filter(groups__in=groups).exclude(groups__in=excluded)
