import urllib.parse

import post_office.models
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

import tracker.auth

from . import util

AuthUser = get_user_model()

TEST_AUTH_MAIL_TEMPLATE = post_office.models.EmailTemplate(
    content='user:{{user}}\nurl:{{reset_url}}\npassword_reset_url:{{password_reset_url}}'
)


@override_settings(EMAIL_FROM_USER='example@example.com')
class TestRegistrationFlow(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_registration_flow(self):
        request = self.factory.post(reverse('tracker:register'))
        new_user = AuthUser.objects.create(
            username='dummyuser', email='test@email.com', is_active=False
        )
        sent_mail = tracker.auth.send_registration_mail(
            request, new_user, template=TEST_AUTH_MAIL_TEMPLATE
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
