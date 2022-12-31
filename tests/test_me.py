from django.contrib.auth.models import AnonymousUser, Group, Permission
from django.urls import reverse

import tracker.views

from .util import APITestCase


class TestMe(APITestCase):
    def setUp(self):
        super(TestMe, self).setUp()
        self.request = self.factory.get(reverse('tracker:me'))
        self.request.user = self.user

    def test_normal_user(self):
        self.assertEqual(
            self.parseJSON(tracker.views.me(self.request)), {'username': 'test'}
        )

    def test_staff_user(self):
        self.request.user.is_staff = True
        self.request.user.save()
        self.assertEqual(
            self.parseJSON(tracker.views.me(self.request)),
            {'username': 'test', 'staff': True},
        )

    def test_super_user(self):
        self.request.user.is_superuser = True
        self.request.user.save()
        self.assertEqual(
            self.parseJSON(tracker.views.me(self.request)),
            {'username': 'test', 'superuser': True},
        )

    def test_user_with_permissions(self):
        self.request.user.user_permissions.add(
            Permission.objects.get(codename='add_user')
        )
        self.assertEqual(
            self.parseJSON(tracker.views.me(self.request)),
            {'username': 'test', 'permissions': ['auth.add_user']},
        )

    def test_user_with_group_permissions(self):
        group = Group.objects.create(name='Test Group')
        group.permissions.add(Permission.objects.get(codename='add_user'))
        group.user_set.add(self.request.user)
        self.assertEqual(
            self.parseJSON(tracker.views.me(self.request)),
            {'username': 'test', 'permissions': ['auth.add_user']},
        )

    def test_anonymous_user(self):
        self.request.user = AnonymousUser()
        self.assertEqual(
            self.parseJSON(tracker.views.me(self.request), 403),
            {
                'error': 'Permission Denied',
                'exception': '',
            },
        )
