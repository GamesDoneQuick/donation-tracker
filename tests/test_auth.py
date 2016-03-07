import re
import itertools

from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup

import post_office.models

import tracker.auth
import tracker.tests.util as test_util
import tracker.management.auth as mgmt_auth

AuthUser = get_user_model()

TEST_AUTH_MAIL_TEMPLATE = post_office.models.EmailTemplate(content="user:{{user}}\nurl:{{reset_url}}")

class TestRegisterEmailSend(TestCase):

    def test_send_registration_email(self):
        newUser = AuthUser.objects.create(username='dummyuser',email='test@email.com',is_active=False)
        sentMail = tracker.auth.send_registration_mail('', newUser, template=TEST_AUTH_MAIL_TEMPLATE)
        contents = test_util.parse_test_mail(sentMail)
        self.assertEqual(newUser.username, contents['user'][0])
        domainURL,middle,suffix = contents['url'][0].partition('?')
        self.assertEqual(tracker.auth.make_auth_token_url_suffix(newUser), suffix)
     
    def test_send_password_reset_email(self):
        existingUser = AuthUser.objects.create(username='existinguser',email='test@email.com',is_active=True)
        sentMail = tracker.auth.send_password_reset_mail('', existingUser, template=TEST_AUTH_MAIL_TEMPLATE)
        contents = test_util.parse_test_mail(sentMail)
        self.assertEqual(existingUser.username, contents['user'][0])
        domainURL,middle,suffix = contents['url'][0].partition('?')
        self.assertEqual(tracker.auth.make_auth_token_url_suffix(existingUser), suffix)

    def test_send_registration_email_existing_user_fails(self):
        existingUser = AuthUser.objects.create(username='existinguser',email='test@email.com',is_active=True)
        self.assertRaises(Exception, tracker.auth.send_registration_mail('', existingUser, template=TEST_AUTH_MAIL_TEMPLATE))
    
    def test_send_password_reset_new_user_fails(self):
        newUser = AuthUser.objects.create(username='dummyuser',email='test@email.com',is_active=False)
        self.assertRaises(Exception, tracker.auth.send_password_reset_mail('', newUser, template=TEST_AUTH_MAIL_TEMPLATE))

class TestInitializeAuthGroups(TestCase):

    def test_create_default_group(self):
        groupName = 'testgroup'
        perms = [
            'tracker.change_donation',
            'tracker.can_search'
        ]

        groupReturned = mgmt_auth.initialize_group(groupName, perms, verbosity=0)
        groupCreated = AuthGroup.objects.get(name=groupName)
        
        self.assertEqual(groupName, groupReturned.name)
        self.assertEqual(groupName, groupCreated.name)
        self.assertEqual(groupReturned, groupCreated)
        
        groupUser = AuthUser.objects.create(username='test',email='test@email.com',is_active=True)
        groupUser.groups.add(groupCreated)
        groupUser.save()

        for perm in perms:
            self.assertTrue(groupUser.has_perm(perm))
        
        extraPerms = ['tracker.add_donation', 'tracker.change_bid']
        
        # Try some permissions not specified
        for perm in extraPerms:
            self.assertFalse(groupUser.has_perm(perm))

        # Test appending to an existing group
        groupReturned2 = mgmt_auth.initialize_group(groupName, extraPerms, set_to_default=False, verbosity=0)
        
        self.assertEqual(groupReturned, groupReturned2)
            
        groupUser = AuthUser.objects.get(pk=groupUser.pk)
            
        for perm in itertools.chain(perms, extraPerms):
            self.assertTrue(groupUser.has_perm(perm))

        stillMorePerms = ['tracker.assign_allowed_group', 'tracker.view_hidden']
        
        for perm in stillMorePerms:
            self.assertFalse(groupUser.has_perm(perm))
        
        # Test re-setting a group wholesale
        groupReturned3 = mgmt_auth.initialize_group(groupName, stillMorePerms, set_to_default=True, verbosity=0)

        self.assertEqual(groupReturned, groupReturned3)
         
        groupUser = AuthUser.objects.get(pk=groupUser.pk)
         
        for perm in stillMorePerms:
            self.assertTrue(groupUser.has_perm(perm))
        
        for perm in itertools.chain(perms, extraPerms):
            self.assertFalse(groupUser.has_perm(perm))
