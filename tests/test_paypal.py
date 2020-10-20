from paypal.standard.ipn.models import PayPalIPN

from .util import MigrationsTestCase, today_noon, long_ago_noon


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
        # test is leaky, but this is the only model that causes logging spew during later migrations
        PayPalIPN.objects.all().delete()


class TestPayPalIPNMigrationsForward(TestPayPalIPNMigrationsBase):
    migrate_from = [('tracker', '0015_add_paypal_tables')]
    migrate_to = [('tracker', '0016_migrate_paypal_data')]

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
            self.unverified_donation.donor.paypal_ipn_info.payer_verified,
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
            self.existing_donor.paypal_ipn_info.payer_verified,
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
    migrate_from = [('tracker', '0016_migrate_paypal_data')]
    migrate_to = [('tracker', '0015_add_paypal_tables')]

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
