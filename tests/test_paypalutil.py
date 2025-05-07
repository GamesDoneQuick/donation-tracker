from unittest import mock

from paypal.standard.ipn.models import PayPalIPN

from tests.util import APITestCase, create_ipn
from tracker import models, paypalutil


@mock.patch('tracker.tasks.post_donation_to_postbacks')
class TestIPNProcessing(APITestCase):
    def setUp(self):
        super().setUp()
        self.donation = models.Donation.objects.create(
            event=self.event, amount=10, domain='PAYPAL'
        )

    def test_first_time_donor(self, task):
        self.donation.requestedalias = 'Famous'
        self.donation.save()

        ipn = create_ipn(
            self.donation,
            'doe@example.com',
            first_name='Jesse',
            last_name='Doe',
            address_street='123 Standard St',
            address_city='Metropolis',
            address_state='NY',
            address_zip='12345',
            address_country_code='US',
        )

        self.assertEqual(paypalutil.get_ipn_donation(ipn), self.donation)
        task.assert_called_with(self.donation.id)

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.transactionstate, 'COMPLETED')
        self.assertEqual(self.donation.domainId, ipn.txn_id)
        self.assertEqual(self.donation.fee, ipn.mc_fee)
        self.assertEqual(self.donation.currency, ipn.mc_currency)
        donor = self.donation.donor
        self.assertEqual(donor.alias, 'Famous')
        self.assertEqual(donor.email, ipn.payer_email)
        self.assertEqual(donor.paypalemail, ipn.payer_email)
        self.assertEqual(donor.firstname, ipn.first_name)
        self.assertEqual(donor.lastname, ipn.last_name)
        self.assertEqual(donor.addressstreet, ipn.address_street)
        self.assertEqual(donor.addresscity, ipn.address_city)
        self.assertEqual(donor.addressstate, ipn.address_state)
        self.assertEqual(donor.addresszip, ipn.address_zip)
        self.assertEqual(donor.addresscountry.alpha2, 'US')

    def test_existing_donor(self, task):
        donor = models.Donor.objects.create(
            email='doe@example.com', paypalemail='doe@example.com'
        )
        ipn = create_ipn(self.donation, donor.paypalemail)

        self.assertEqual(paypalutil.get_ipn_donation(ipn), self.donation)
        task.assert_called_with(self.donation.id)

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.transactionstate, 'COMPLETED')
        donor.refresh_from_db()
        self.assertEqual(self.donation.donor, donor)

    def test_email_match_is_okay(self, task):
        ipn = PayPalIPN(business='Charity@example.com')
        paypalutil.verify_ipn_recipient_email(ipn, 'charity@example.com')

        ipn = PayPalIPN(receiver_email='ChArItY@example.com')
        paypalutil.verify_ipn_recipient_email(ipn, 'charity@example.com')

    def test_email_mismatch_raises_exception(self, task):
        ipn = create_ipn(
            self.donation, 'doe@example.com', business='notthecharity@example.com'
        )
        with self.assertRaises(paypalutil.SpoofedIPNException):
            paypalutil.verify_ipn_recipient_email(ipn, 'charity@example.com')
        self.assertIsNone(paypalutil.get_ipn_donation(ipn))

        ipn = create_ipn(
            self.donation, 'doe@example.com', receiver_email='notthecharity@example.com'
        )
        with self.assertRaises(paypalutil.SpoofedIPNException):
            paypalutil.verify_ipn_recipient_email(ipn, 'charity@example.com')
        self.assertIsNone(paypalutil.get_ipn_donation(ipn))

        task.assert_not_called()

    def test_set_cleared_at(self, task):
        ipn = create_ipn(self.donation, 'doe@example.com')

        self.assertEqual(paypalutil.get_ipn_donation(ipn), self.donation)
        task.assert_called_with(self.donation.id)

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.cleared_at, ipn.created_at)

    def test_use_celery(self, task):
        with self.settings(TRACKER_HAS_CELERY=True):
            ipn = create_ipn(self.donation, 'doe@example.com')

            self.assertEqual(paypalutil.get_ipn_donation(ipn), self.donation)
            task.delay.assert_called_with(self.donation.id)
            task.assert_not_called()

    def test_amount_mismatch_is_ignored(self, task):
        ipn = create_ipn(self.donation, 'doe@example.com', mc_gross=5)

        self.assertIsNone(paypalutil.get_ipn_donation(ipn))

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.transactionstate, 'PENDING')
        self.assertIsNone(self.donation.donor)
        task.assert_not_called()

    def test_custom_mismatch_is_ignored(self, task):
        bid = models.Bid.objects.create(event=self.event, istarget=True)
        self.donation.bids.create(bid=bid, amount=10)
        ipn = create_ipn(self.donation, 'doe@example.com')

        self.assertEqual(paypalutil.get_ipn_donation(ipn), self.donation)

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.transactionstate, 'COMPLETED')
        self.assertEqual(self.donation.donor.paypalemail, 'doe@example.com')
        task.assert_called_with(self.donation.id)
        task.reset_mock()

        ipn = create_ipn(
            self.donation, 'eod@example.com', custom=f'{self.donation.id}:feedbeef'
        )
        self.assertIsNone(paypalutil.get_ipn_donation(ipn))

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.donor.paypalemail, 'doe@example.com')
        task.assert_not_called()

    def test_flagged(self, task):
        ipn = create_ipn(self.donation, 'doe@example.com', flag=True)

        self.assertEqual(paypalutil.get_ipn_donation(ipn), self.donation)

        self.donation.refresh_from_db()
        self.assertEqual(self.donation.transactionstate, 'FLAGGED')
        task.assert_not_called()
