from django.contrib.admin import models
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext as _
from django.utils.encoding import force_unicode
from django.utils.text import get_text_list

def get_change_message(fields):
    """
    Create a change message for *fields* (a sequence of field names).
    """
    return _('Changed %s.') % get_text_list(fields, _('and'))

def addition(request, object):
    """
    Log that an object has been successfully added.
    """
    models.LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_unicode(object),
        action_flag=models.ADDITION
    )

def change(request, object, message_or_fields):
    """
    Log that an object has been successfully changed.

    The argument *message_or_fields* must be a sequence of modified field names
    or a custom change message.
    """
    if isinstance(message_or_fields, basestring):
        message = message_or_fields
    else:
        message = get_change_message(message_or_fields)
    models.LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(object).pk,
        object_id=object.pk,
        object_repr=force_unicode(object),
        action_flag=models.CHANGE,
        change_message=message
    )

def deletion(request, object, object_repr=None):
    """
    Log that an object will be deleted.
    """
    models.LogEntry.objects.log_action(
        user_id=request.user.id,
        content_type_id=ContentType.objects.get_for_model(object).pk,
        object_id=object.pk,
        object_repr=object_repr or force_unicode(object),
        action_flag=models.DELETION
    )

def in_bulk(request, added, changed, deleted):
    """
    Log all *added*, *changed* and *deleted* instances.

    Note that, while *added* and *deleted* are sequences of instances,
    *changed* must be a sequence of tuples *(instance, message_or_fields)*,
    where *message_or_fields* is a sequence of modified field names
    or a custom change message.
    """
    for instance in added:
        addition(request, instance)
    for instance, fields in changed:
        if fields:
            change(request, instance, fields)
    for instance in deleted:
        deletion(request, instance)


class AdminLogMixin(object):
    """
    Class based views mixin that adds simple wrappers to
    the three functions above.
    """
    def log_addition(self, instance):
        """
        Log that an object has been successfully added.
        """
        addition(self.request, instance)

    def log_change(self, instance, message_or_fields):
        """
        Log that an object has been successfully changed.
        """
        change(self.request, instance, message_or_fields)

    def log_deletion(self, instance, instance_repr=None):
        """
        Log that an object will be deleted.
        """
        deletion(self.request, instance, instance_repr)

    def logall(self, added, changed, deleted):
        in_bulk(self.request, added, changed, deleted)


class AdminLogger(AdminLogMixin):
    """
    A more generic Python object that can be used as a logger
    taking the request in the constructor.
    """
    def __init__(self, request):
        self.request = request


class AdminLogCollector(object):
    """
    A class to collect logs that will be reported later.

    It can be useful, for example, when you need to add log entries
    in forms (e.g. in a custom admin page) without the need to pass a
    request argument::

        class MyForm(forms.Form):
            def __init__(self, *args, **kwargs):
                super(MyForm, self).__init__(*args, **kwargs)
                self.collector = AdminLogCollector()

            def save(self):
                ... add some instance
                self.collector.added(instance)

    If you have a formset of forms like the above, it is easy to
    collect all logs::

        class MyBaseFormSet(BaseFormSet):
            def save(self):
                collectors = []
                for form in self.forms:
                    form.save()
                    collectors.append(form.collector)
                # collect changes for all forms
                self.collector = sum(collectors, AdminLogCollector())
                # return the number of forms that did something
                return len(filter(None, collectors))

    In the view you can actually save all collected log entries::

        formset.collector.logall(request)
    """
    def __init__(self, added=None, changed=None, deleted=None, logger=None):
        self._added = set() if added is None else set(added)
        self._changed = set() if changed is None else set(changed)
        self._deleted = set() if deleted is None else set(deleted)
        self._logger = logger or in_bulk
        self._done = False

    def __add__(self, other):
        added, changed, deleted = other.get_collected()
        return self.__class__(
            self._added.union(added),
            self._changed.union(changed),
            self._deleted.union(deleted),
            logger=self._logger
        )

    def __repr__(self):
        return repr(self.get_collected())

    def __nonzero__(self):
        return any(self.get_collected())

    def added(self, instance):
        """
        Collect an addition log.
        """
        self._added.add(instance)

    def changed(self, instance, message_or_fields):
        """
        Collect a change log.
        """
        if not isinstance(message_or_fields, basestring):
            message_or_fields = tuple(message_or_fields)
        self._changed.add((instance, message_or_fields))

    def deleted(self, instance):
        """
        Collect a deletion log.
        """
        self._deleted.add(instance)

    def get_collected(self):
        """
        Return a tuple *(additions, changes, deletions)*
        representing all the collected logs.
        """
        return self._added, self._changed, self._deleted

    def logall(self, request, redo=False):
        """
        Actually save all log entries using the given *request*.
        """
        if redo or not self._done:
            self._logger(request, self._added, self._changed, self._deleted)
            self._done = True
