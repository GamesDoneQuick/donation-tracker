from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model

AuthUser = get_user_model()

import settings

import tracker.forms

class TestRegistrationForm(TransactionTestCase):

    def run_registration(self, email):
        regForm = tracker.forms.RegistrationForm(data={'email': email, 'from_email': email})
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
        regEmail = 'test'*9 + '@anothertest.com'
        userObj = self.run_registration(regEmail)
        self.assertGreaterEqual(30, len(userObj.username))
        self.assertEqual(regEmail, userObj.email)
        self.assertFalse(userObj.is_active)
        self.assertFalse(userObj.is_staff)
    
    def testClashingRegistrationEmails(self):
        regEmailPrefix = 'prefix'*9
        self.assertLess(30, len(regEmailPrefix))
        regEmail1 = regEmailPrefix + '@test1.com'
        regEmail2 = regEmailPrefix + '@test2.com'
        userObj1 = self.run_registration(regEmail1)
        userObj2 = self.run_registration(regEmail2)
        self.assertNotEqual(userObj1, userObj2)
