from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.test import TestCase, TransactionTestCase, RequestFactory
from django.test import override_settings
from django.urls import reverse

import tracker.forms
from tracker.models import Donor

AuthUser = get_user_model()


class TestMergeObjectsForm(TestCase):
    def test_unambiguous_object_names(self):
        d1 = Donor.objects.create(alias='Justin')

        form = tracker.forms.MergeObjectsForm(
            model=tracker.models.Donor, objects=[d1.pk]
        )
        self.assertEqual(form.choices[0][1], '#%d: Justin' % d1.pk)


@override_settings(EMAIL_FROM_USER='example@example.com')
class TestRegistrationForm(TransactionTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def run_registration(self, email):
        reg_form = tracker.forms.RegistrationForm(
            data={'email': email, 'from_email': email}
        )
        self.assertTrue(reg_form.is_valid())
        result_mail = reg_form.save(
            request=self.factory.post(reverse('tracker:register'))
        )
        self.assertIsNot(None, result_mail)
        result_user_query = AuthUser.objects.filter(email=email)
        self.assertEqual(1, result_user_query.count())
        return result_user_query[0]

    def test_register_person(self):
        reg_email = 'testemail@test.com'
        user_obj = self.run_registration(reg_email)
        self.assertEqual(reg_email, user_obj.username)
        self.assertEqual(reg_email, user_obj.email)
        self.assertFalse(user_obj.is_active)
        self.assertFalse(user_obj.is_staff)

    def test_register_person_long_email(self):
        reg_email = 'test' * 9 + '@anothertest.com'
        user_obj = self.run_registration(reg_email)
        self.assertGreaterEqual(30, len(user_obj.username))
        self.assertEqual(reg_email, user_obj.email)
        self.assertFalse(user_obj.is_active)
        self.assertFalse(user_obj.is_staff)

    def test_clashing_registration_emails(self):
        reg_email_prefix = 'prefix' * 9
        self.assertLess(30, len(reg_email_prefix))
        reg_email1 = reg_email_prefix + '@test1.com'
        reg_email2 = reg_email_prefix + '@test2.com'
        user1 = self.run_registration(reg_email1)
        user2 = self.run_registration(reg_email2)
        self.assertNotEqual(user1, user2)


class TestRegistrationConfirmationForm(TransactionTestCase):
    def test_username_normalization(self):
        user = AuthUser.objects.create(username='foo@example.com', is_active=False)
        token_generator = default_token_generator
        form = tracker.forms.RegistrationConfirmationForm(
            user,
            token_generator.make_token(user),
            token_generator,
            data={
                'username': '\uFB01',
                'password': 'password',
                'passwordconfirm': 'password',
            },
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['username'], 'fi')
