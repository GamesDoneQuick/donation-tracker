import urllib.parse

import post_office.models
from django.contrib.auth import get_user_model
from django.contrib.sites.models import Site
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

import tracker.auth

from . import util
from .util import MigrationsTestCase

AuthUser = get_user_model()


@override_settings(TRACKER_REGISTRATION_FROM_EMAIL='example@example.com')
class TestRegistrationFlow(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.template = post_office.models.EmailTemplate.objects.create(
            content='user:{{user}}\nurl:{{confirmation_url}}\npassword_reset_url:{{password_reset_url}}'
        )
        Site.objects.create(domain='testserver', name='Test Server')

    def test_registration_flow(self):
        request = self.factory.post(reverse('tracker:register'))
        new_user = AuthUser.objects.create(
            username='dummyuser', email='test@email.com', is_active=False
        )
        sent_mail = tracker.auth.send_registration_mail(
            request, new_user, template=self.template
        )
        contents = util.parse_test_mail(sent_mail)
        self.assertEqual(new_user.username, contents['user'][0])
        parsed = urllib.parse.urlparse(contents['url'][0])
        self.assertIn(
            reverse('tracker:password_reset'), contents['password_reset_url'][0]
        )
        resp = self.client.get(parsed.path)
        expected_url = reverse(
            'tracker:confirm_registration',
            kwargs={
                'uidb64': urlsafe_base64_encode(force_bytes(new_user.pk)),
                'token': 'register-user',
            },
        )
        self.assertRedirects(resp, expected_url)
        resp = self.client.get(expected_url)
        self.assertContains(resp, 'Please set your username and password.')
        resp = self.client.post(
            expected_url,
            {
                'username': 'dummyuser',
                'password': 'foobar',
                'passwordconfirm': 'foobar',
            },
        )
        self.assertContains(resp, 'Your user account has been confirmed')
        new_user.refresh_from_db()
        self.assertTrue(new_user.is_active)
        self.assertTrue(new_user.check_password('foobar'))

    def test_reset_url_deprecation(self):
        with self.assertRaises(AssertionError):
            request = self.factory.post(reverse('tracker:register'))
            new_user = AuthUser.objects.create(
                username='dummyuser', email='test@email.com', is_active=False
            )
            template = post_office.models.EmailTemplate.objects.create(
                content='{{ reset_url }}'
            )
            tracker.auth.send_registration_mail(request, new_user, template=template)

    def test_register_inactive_user(self):
        AuthUser.objects.create(
            username='existinguser', email='test@email.com', is_active=False
        )
        resp = self.client.post(
            reverse('tracker:register'), data={'email': 'test@email.com'}
        )
        self.assertContains(resp, 'An e-mail has been sent to your address.')

    def test_register_active_user(self):
        AuthUser.objects.create(
            username='existinguser', email='test@email.com', is_active=True
        )
        resp = self.client.post(
            reverse('tracker:register'), data={'email': 'test@email.com'}
        )
        self.assertFormError(
            resp.context['form'],
            'email',
            [
                'This email is already registered. Please log in, (or reset your password if you forgot it).'
            ],
        )


class TestPermissionsMigrationForwards(MigrationsTestCase):
    migrate_from = [('tracker', '0041_permissions_pass')]
    migrate_to = [('tracker', '0042_search_permissions_rename')]

    def setUpBeforeMigration(self, apps):
        User = apps.get_model('auth', 'user')
        Group = apps.get_model('auth', 'group')
        Permission = apps.get_model('auth', 'permission')

        user = User.objects.create(username='user')
        group = Group.objects.create(name='group')
        old = Permission.objects.get(
            content_type__app_label='tracker',
            content_type__model='userprofile',
            codename='can_search',
        )
        old.user_set.add(user)
        old.group_set.add(group)
        old = Permission.objects.get(
            content_type__app_label='tracker',
            content_type__model='donor',
            codename='view_usernames',
        )
        old.user_set.add(user)
        old.group_set.add(group)

    def test_forwards(self):
        from django.contrib.auth.models import Group, User

        user = User.objects.get(username='user')
        group = Group.objects.get(name='group')
        self.permissions_helper(
            user,
            group,
            {'app_label': 'tracker', 'model': 'userprofile', 'codename': 'can_search'},
            {
                'app_label': 'tracker',
                'model': 'userprofile',
                'codename': 'can_search_for_user',
            },
            True,
        )
        self.permissions_helper(
            user,
            group,
            {'app_label': 'tracker', 'model': 'donor', 'codename': 'view_usernames'},
            {'app_label': 'tracker', 'model': 'donor', 'codename': 'view_full_names'},
            True,
        )


class TestPermissionsMigrationBackwards(MigrationsTestCase):
    migrate_from = [('tracker', '0042_search_permissions_rename')]
    migrate_to = [('tracker', '0041_permissions_pass')]

    def setUpBeforeMigration(self, apps):
        User = apps.get_model('auth', 'user')
        Group = apps.get_model('auth', 'group')
        Permission = apps.get_model('auth', 'permission')

        user = User.objects.create(username='user')
        group = Group.objects.create(name='group')
        new = Permission.objects.get(
            content_type__app_label='tracker',
            content_type__model='userprofile',
            codename='can_search_for_user',
        )
        new.user_set.add(user)
        new.group_set.add(group)
        new = Permission.objects.get(
            content_type__app_label='tracker',
            content_type__model='donor',
            codename='view_full_names',
        )
        new.user_set.add(user)
        new.group_set.add(group)

    def test_backwards(self):
        from django.contrib.auth.models import Group, User

        user = User.objects.get(username='user')
        group = Group.objects.get(name='group')
        self.permissions_helper(
            user,
            group,
            {
                'app_label': 'tracker',
                'model': 'userprofile',
                'codename': 'can_search_for_user',
            },
            {'app_label': 'tracker', 'model': 'userprofile', 'codename': 'can_search'},
            False,
        )
        self.permissions_helper(
            user,
            group,
            {'app_label': 'tracker', 'model': 'donor', 'codename': 'view_full_names'},
            {'app_label': 'tracker', 'model': 'donor', 'codename': 'view_usernames'},
            False,
        )
