import random
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from paypal.standard.ipn.models import PayPalIPN
from tracker import models

from . import randgen
from .util import APITestCase, MigrationsTestCase, long_ago_noon, today_noon


class TestPayPalIPNMigrationsBase(MigrationsTestCase):
    def setUp(self):
        with self.assertLogs('tracker.migrations', 'WARNING') as logs:
            super(TestPayPalIPNMigrationsBase, self).setUp()
        self.logs = logs

    def setUpBeforeMigration(self, apps):
        PayPalIPN = apps.get_model('ipn', 'paypalipn')
        Donation = apps.get_model('tracker', 'donation')
        Donor = apps.get_model('tracker', 'donor')
        Event = apps.get_model('tracker', 'event')
        self.event = Event.objects.create(
            short='test',
            name='test_event',
            datetime=today_noon,
            paypalemail='foobar@example.com',
            paypalcurrency='USD',
            paypalimgurl='foobar.jpg',
        )
        # to test the logging
        self.unknown_custom_ipn = PayPalIPN.objects.create(custom='asdf')
        self.missing_donation_ipn = PayPalIPN.objects.create(custom='10000:100')
        self.existing_donor = Donor.objects.create(
            paypalemail='baz@example.com', alias='Baz', alias_num=1234
        )
        self.unverified_donation = Donation.objects.create(
            event=self.event,
            amount=5,
            domainId='deadbeef',
            donor=self.existing_donor,
            requestedalias='Baz',
        )
        self.unverified_donation_ipn = PayPalIPN.objects.create(
            custom=f'{self.unverified_donation.pk}:{self.unverified_donation.domainId}',
            payer_id='deadbead',
            payer_email='baz@example.com',
            payer_status='unverified',
            payment_date=long_ago_noon,
        )
        self.verified_donation = Donation.objects.create(
            event=self.event,
            amount=5,
            domainId='deafbeef',
            donor=self.existing_donor,
            requestedalias='Baz',
        )
        self.verified_donation_ipn = PayPalIPN.objects.create(
            custom=f'{self.verified_donation.pk}:{self.verified_donation.domainId}',
            payer_id='deafbead',
            payer_email='baz@example.com',
            payer_status='verified',
            payment_date=today_noon,
        )

    def tearDown(self):
        # prevents logging spew during the re-migration
        PayPalIPN.objects.all().delete()
        super(TestPayPalIPNMigrationsBase, self).tearDown()


class TestPayPalIPNMigrationsForward(TestPayPalIPNMigrationsBase):
    migrate_from = [('tracker', '0016_add_paypal_tables')]
    migrate_to = [('tracker', '0017_migrate_paypal_data')]

    def test_migrated_data(self):
        self.assertIn('Could not parse custom', self.logs.records[0].message)
        self.assertIn('does not exist', self.logs.records[1].message)

        self.unverified_donation.refresh_from_db()
        self.assertIn(self.unverified_donation_ipn, self.unverified_donation.ipn.all())
        self.assertNotEqual(self.unverified_donation.donor, self.existing_donor)
        self.assertEqual(
            self.unverified_donation.donor.paypalemail, 'unverified-baz@example.com'
        )
        self.assertFalse(
            self.unverified_donation.donor.paypal_info.payer_verified,
            msg='Payer should not be verified',
        )
        self.assertEqual(self.unverified_donation.donor.alias, 'Baz')
        self.assertIsNot(
            self.unverified_donation.donor.alias_num, None, msg='Alias number missing'
        )

        self.verified_donation.refresh_from_db()
        self.assertIn(self.verified_donation_ipn, self.verified_donation.ipn.all())
        self.assertEqual(self.verified_donation.donor, self.existing_donor)
        self.assertEqual(self.existing_donor.paypalemail, 'baz@example.com')
        self.assertTrue(
            self.existing_donor.paypal_info.payer_verified,
            msg='Payer should be verified',
        )

        self.assertEqual(
            self.event.paypal_ipn_settings.receiver_email, self.event.paypalemail
        )
        self.assertEqual(
            self.event.paypal_ipn_settings.currency, self.event.paypalcurrency
        )
        self.assertEqual(
            self.event.paypal_ipn_settings.logo_url, self.event.paypalimgurl
        )


class TestPayPalIPNMigrationsReverse(TestPayPalIPNMigrationsBase):
    migrate_from = [('tracker', '0017_migrate_paypal_data')]
    migrate_to = [('tracker', '0016_add_paypal_tables')]

    def setUpBeforeMigration(self, apps):
        super(TestPayPalIPNMigrationsReverse, self).setUpBeforeMigration(apps)
        Donor = apps.get_model('tracker', 'donor')
        self.unverified_donor = Donor.objects.create(
            paypalemail='unverified-baz@example.com', alias='Baz', alias_num=1235
        )

    def test_migrated_data(self):
        self.assertIn('Could not parse custom', self.logs.records[0].message)
        self.assertIn('does not exist', self.logs.records[1].message)

        self.unverified_donation.refresh_from_db()
        self.assertEqual(self.unverified_donation.donor, self.existing_donor)

        self.verified_donation.refresh_from_db()
        self.assertEqual(self.verified_donation.donor, self.existing_donor)


class TestPayPalAdmin(APITestCase):
    def test_ipn_settings_admin(self):
        event = randgen.generate_event(self.rand)
        event.save()
        ipn_settings = models.IPNSettings.objects.create(
            event=event, receiver_email='foo@example.com'
        )
        self.client.force_login(self.super_user)
        response = self.client.get(reverse('admin:tracker_ipnsettings_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('admin:tracker_ipnsettings_add'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse('admin:tracker_ipnsettings_change', args=(ipn_settings.id,))
        )
        self.assertEqual(response.status_code, 200)

    def test_donor_paypal_info_admin(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        donor_paypal_info = models.DonorPayPalInfo.objects.create(
            donor=donor,
            payer_id='deadbeef',
            payer_email=donor.email,
            payer_verified=False,
        )
        self.client.force_login(self.super_user)
        response = self.client.get(reverse('admin:tracker_donorpaypalinfo_changelist'))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(
            reverse(
                'admin:tracker_donorpaypalinfo_change', args=(donor_paypal_info.id,)
            )
        )
        self.assertEqual(response.status_code, 200)


class TestProcessIPN(TestCase):
    def setUp(self):
        self.rand = random.Random()
        self.event = randgen.generate_event(self.rand, today_noon)
        self.event.save()
        self.ipn_settings = models.IPNSettings.objects.create(
            event=self.event, receiver_email='bar@example.com'
        )
        self.donation = randgen.generate_donation(
            self.rand,
            event=self.event,
            no_donor=True,
            min_amount=5,
            domain='PAYPAL',
            transactionstate='PENDING',
        )
        self.donation.requestedalias = 'Foo'
        self.donation.requestedemail = 'foo+requested@example.com'
        self.donation.save()
        self.base_ipn = PayPalIPN.objects.create(
            custom=f'{self.donation.id}:{self.donation.domainId}',
            business='bar@example.com',
            payer_email='foo@example.com',
            payer_id='0XWAS',
            payer_status='unverified',
            first_name='Foo',
            last_name='Bar',
            address_street='123 Somewhere Ave',
            address_city='Atlantis',
            address_state='NJ',
            address_zip='20000',
            address_country_code='US',
            txn_id='deadbeef',
            mc_gross=self.donation.amount,
            mc_currency='USD',
            mc_fee=Decimal('0.25'),
            payment_date=today_noon,
            payment_status='completed',
        )

    def test_invalid_ipn(self):
        ipn = PayPalIPN.objects.create(
            custom=f'{self.donation.id}:{self.donation.domainId}',
            flag_info='This is bunk',
            flag=True,
        )
        with self.assertLogs('tracker') as logs:
            ipn.send_signals()
        self.assertIn('Invalid IPN', logs.records[0].message)

    def test_missing_custom_field(self):
        ipn = PayPalIPN.objects.create()
        ipn.send_signals()
        self.assertIn('No donation found for IPN', models.Log.objects.last().message)

    def test_invalid_custom_field(self):
        ipn = PayPalIPN.objects.create(custom='asdf')
        with self.assertLogs('tracker') as logs:
            ipn.send_signals()
        self.assertIn('No donation found for IPN', models.Log.objects.last().message)
        self.assertIn('Unknown custom field for IPN', logs.records[0].message)

    def test_spoofed_receiver(self):
        self.base_ipn.business = 'spoofed@example.com'
        with self.assertLogs('tracker') as logs:
            self.base_ipn.send_signals()
        self.assertEqual(self.donation.transactionstate, 'PENDING')
        self.assertIn('Spoofed IPN', models.Log.objects.last().message)
        self.assertIn('Spoofed IPN', logs.records[0].message)

    @patch('tracker.tasks.post_donation_to_postbacks')
    def test_completed_ipn_new_donor(self, task):
        # also the primary test for a lot of the happy path
        self.base_ipn.send_signals()
        self.donation.refresh_from_db()
        self.assertEqual(self.donation.transactionstate, 'COMPLETED')
        self.assertEqual(self.donation.domainId, self.base_ipn.txn_id)
        self.assertEqual(self.donation.fee, self.base_ipn.mc_fee)
        self.assertEqual(self.donation.donor.email, self.donation.requestedemail)
        self.assertEqual(self.donation.donor.alias, self.donation.requestedalias)
        self.assertIsNot(
            self.donation.donor.alias_num, None, msg='Alias number not filled in'
        )
        self.assertEqual(self.donation.donor.firstname, self.base_ipn.first_name)
        self.assertEqual(self.donation.donor.lastname, self.base_ipn.last_name)
        self.assertEqual(
            self.donation.donor.addressstreet, self.base_ipn.address_street
        )
        self.assertEqual(self.donation.donor.addresscity, self.base_ipn.address_city)
        self.assertEqual(self.donation.donor.addressstate, self.base_ipn.address_state)
        self.assertEqual(
            self.donation.donor.addresscountry,
            models.Country.objects.get(alpha2=self.base_ipn.address_country_code),
        )
        self.assertEqual(self.donation.donor.addresszip, self.base_ipn.address_zip)
        self.assertEqual(
            self.donation.donor.paypal_info.payer_email, self.base_ipn.payer_email
        )
        self.assertEqual(
            self.donation.donor.paypal_info.payer_id, self.base_ipn.payer_id
        )
        self.assertFalse(self.donation.donor.paypal_info.payer_verified)
        task.assert_called_with(self.donation.id)

    @patch('tracker.tasks.post_donation_to_postbacks')
    @override_settings(HAS_CELERY=True)
    def test_completed_ipn_with_celery(self, task):
        self.base_ipn.send_signals()
        task.delay.assert_called_with(self.donation.id)

    def test_completed_ipn_existing_donor_matching_id(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        models.DonorPayPalInfo.objects.create(
            donor=donor,
            payer_id=self.base_ipn.payer_id,
            payer_email='foo@different-example.org',
            payer_verified=self.base_ipn.payer_status == 'verified',
        )
        self.base_ipn.send_signals()
        self.donation.refresh_from_db()
        donor.refresh_from_db()
        self.assertEqual(self.donation.donor, donor)
        self.assertEqual(donor.email, self.donation.requestedemail)
        self.assertEqual(donor.alias, self.donation.requestedalias)
        self.assertIsNot(donor.alias_num, None, msg='Alias number not filled in')
        self.assertEqual(donor.solicitemail, self.donation.requestedsolicitemail)
        self.assertEqual(donor.paypal_info.payer_email, self.base_ipn.payer_email)

    def test_completed_ipn_existing_donor_matching_email(self):
        donor = randgen.generate_donor(self.rand)
        donor.save()
        models.DonorPayPalInfo.objects.create(
            donor=donor,
            payer_id='deadbeef',
            payer_email=self.base_ipn.payer_email,
            payer_verified=self.base_ipn.payer_status == 'verified',
        )
        self.base_ipn.send_signals()
        self.donation.refresh_from_db()
        donor.refresh_from_db()
        self.assertEqual(self.donation.donor, donor)
        self.assertEqual(donor.email, self.donation.requestedemail)
        self.assertEqual(donor.alias, self.donation.requestedalias)
        self.assertIsNot(donor.alias_num, None, msg='Alias number not filled in')
        self.assertEqual(donor.solicitemail, self.donation.requestedsolicitemail)
        self.assertEqual(donor.paypal_info.payer_id, self.base_ipn.payer_id)

    def test_completed_ipn_amount_mismatch(self):
        bid1 = randgen.generate_bid(
            self.rand, add_goal=True, max_depth=0, event=self.event
        )[0]
        bid1.save()
        bid2 = randgen.generate_bid(
            self.rand, add_goal=True, max_depth=0, event=self.event
        )[0]
        bid2.save()
        models.DonationBid.objects.create(
            bid=bid1, donation=self.donation, amount=self.donation.amount - 1
        )
        models.DonationBid.objects.create(bid=bid2, donation=self.donation, amount=0.5)
        self.base_ipn.mc_gross -= 1
        self.base_ipn.save()
        self.base_ipn.send_signals()
        self.donation.refresh_from_db()
        self.assertFalse(
            self.donation.bids.exists(),
            msg='Bids were not erased after amount mismatch',
        )
        self.assertIn('removed all bids', self.donation.modcomment)
        self.assertIn('removed all bids', models.Log.objects.last().message)
