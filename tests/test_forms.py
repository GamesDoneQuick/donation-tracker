from django.conf import settings
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.test import override_settings

import tracker.forms
from tracker.models import Donor

AuthUser = get_user_model()


class TestMergeObjectsForm(TestCase):
    def test_unambiguous_object_names(self):
        d1 = Donor.objects.create(alias='Justin')

        form = tracker.forms.MergeObjectsForm(
            model=tracker.models.Donor,
            objects=[d1.pk])
        self.assertEqual(form.choices[0][1], '#%d: Justin' % d1.pk)


@override_settings(EMAIL_FROM_USER='example@example.com')
class TestRegistrationForm(TransactionTestCase):

    def run_registration(self, email):
        regForm = tracker.forms.RegistrationForm(
            data={'email': email, 'from_email': email})
        self.assertTrue(regForm.is_valid())
        regForm.save(domain=settings.DOMAIN)
        resultMail = regForm.save(domain=settings.DOMAIN)
        self.assertIsNot(None, resultMail)
        resultUserQuery = AuthUser.objects.filter(email=email)
        self.assertEqual(1, resultUserQuery.count())
        return resultUserQuery[0]

    def testRegisterPerson(self):
        regEmail = 'testemail@test.com'
        userObj = self.run_registration(regEmail)
        self.assertEqual(regEmail, userObj.username)
        self.assertEqual(regEmail, userObj.email)
        self.assertFalse(userObj.is_active)
        self.assertFalse(userObj.is_staff)

    def testRegisterPersonLongEmail(self):
        regEmail = 'test' * 9 + '@anothertest.com'
        userObj = self.run_registration(regEmail)
        self.assertGreaterEqual(30, len(userObj.username))
        self.assertEqual(regEmail, userObj.email)
        self.assertFalse(userObj.is_active)
        self.assertFalse(userObj.is_staff)

    def testClashingRegistrationEmails(self):
        regEmailPrefix = 'prefix' * 9
        self.assertLess(30, len(regEmailPrefix))
        regEmail1 = regEmailPrefix + '@test1.com'
        regEmail2 = regEmailPrefix + '@test2.com'
        userObj1 = self.run_registration(regEmail1)
        userObj2 = self.run_registration(regEmail2)
        self.assertNotEqual(userObj1, userObj2)
