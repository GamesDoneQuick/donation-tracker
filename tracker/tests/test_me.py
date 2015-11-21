import json
from django.core.exceptions import PermissionDenied

from django.test import TransactionTestCase
from django.http import HttpRequest
from django.contrib.auth.models import User, Permission, AnonymousUser
import tracker.views


class TestMe(TransactionTestCase):
    def setUp(self):
        self.request = HttpRequest()
        self.request.user = User.objects.create(username='test')

    def test_normal_user(self):
        self.assertEqual(json.loads(tracker.views.me(self.request).content), { 'username': 'test' })

    def test_staff_user(self):
        self.request.user.is_staff = True
        self.request.user.save()
        self.assertEqual(json.loads(tracker.views.me(self.request).content), { 'username': 'test', 'staff': True })

    def test_super_user(self):
        self.request.user.is_superuser = True
        self.request.user.save()
        self.assertEqual(json.loads(tracker.views.me(self.request).content), { 'username': 'test', 'superuser': True })

    def test_user_with_permissions(self):
        self.request.user.user_permissions.add(Permission.objects.get(codename='add_user'))
        self.assertEqual(json.loads(tracker.views.me(self.request).content), { 'username': 'test', 'permissions': ['auth.add_user'] })

    def test_anonymous_user(self):
        self.request.user = AnonymousUser()
        with self.assertRaises(PermissionDenied):
            tracker.views.me(self.request)
