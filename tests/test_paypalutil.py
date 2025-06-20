from unittest import mock

from paypal.standard.ipn.models import PayPalIPN

from tests import util
from tests.util import APITestCase, create_ipn
from tracker import models, paypalutil, settings


@mock.patch('tracker.tasks.post_donation_to_postbacks')
class TestIPNProcessing(APITestCase):
    def setUp(self):
        super().setUp()
        self.donation = models.Donation.objects.create(
            event=self.event, amount=10, domain='PAYPAL', transactionstate='PENDING'
        )

    def assertDonation(
        self,
        task,
        email,
        ipn_args,
        /,
        *,
        matches=True,
        changes=None,
        donor=None,
        **kwargs,
    ):
        old = self.donation.__dict__
        task.reset_mock()
        self.ipn = create_ipn(self.donation, email, **ipn_args)
        if donor:
            kwargs['donor_id'] = donor.id
        if changes is None:
            changes = matches and bool(kwargs)
        self.donation.refresh_from_db()
        if matches:
            self.assertEqual(self.donation, paypalutil.get_ipn_donation(self.ipn))
        else:
            self.assertIsNone(paypalutil.get_ipn_donation(self.ipn))
            task.delay.assert_not_called()
            task.assert_not_called()
        if changes:
            if not self.ipn.flag:
                if settings.TRACKER_HAS_CELERY:
                    task.delay.assert_called_with(self.donation.id)
                    task.assert_not_called()
                else:
                    task.delay.assert_not_called()
                    task.assert_called_with(self.donation.id)
                self.assertEqual(self.donation.domainId, self.ipn.txn_id)
                self.assertEqual(self.donation.cleared_at, self.ipn.created_at)
            self.assertDictContainsSubset(
                kwargs, self.donation.__dict__, 'Donation state mismatch'
            )
        else:
            self.assertEqual(old, self.donation.__dict__, 'Donation state changed')

    def assertDonor(self, **kwargs):
        self.donation.refresh_from_db()
        donor = self.donation.donor
        self.assertIsNotNone(donor, 'Donation has no donor')
        country = models.Country.objects.filter(
            alpha2=self.ipn.address_country_code
        ).first()
        kwargs.update(
            dict(
                email=self.ipn.payer_email,
                paypalemail=self.ipn.payer_email,
                firstname=self.ipn.first_name,
                lastname=self.ipn.last_name,
                addressstreet=self.ipn.address_street,
                addresscity=self.ipn.address_city,
                addressstate=self.ipn.address_state,
                addresszip=self.ipn.address_zip,
                addresscountry_id=country.id if country else None,
            )
        )
        self.assertDictContainsSubset(kwargs, donor.__dict__, 'Donor state mismatch')

    def test_first_time_donor(self, task):
        self.donation.requestedalias = 'Famous'
        self.donation.save()

        with self.assertTrackerLogs(1):
            self.assertDonation(
                task,
                'doe@example.com',
                dict(
                    first_name='Jesse',
                    last_name='Doe',
                    address_street='123 Standard St',
                    address_city='Metropolis',
                    address_state='NY',
                    address_zip='12345',
                    address_country_code='US',
                ),
                transactionstate='COMPLETED',
            )
            self.assertDonor(
                alias='Famous',
            )

    def test_existing_donor(self, task):
        donor = models.Donor.objects.create(
            email='doe@example.com', paypalemail='doe@example.com'
        )

        self.assertDonation(
            task, donor.paypalemail, {}, transactionstate='COMPLETED', donor=donor
        )

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

    def test_amount_mismatch_fails_validation(self, task):
        with self.assertTrackerLogs(3, 'paypal'):
            self.assertDonation(
                task, 'doe@example.com', dict(mc_gross=5), matches=False
            )

    def test_custom_mismatch_fails_validation(self, task):
        create_ipn(
            self.donation, 'doe@example.com', custom=f'{self.donation.id}:deadbeef'
        )
        self.donation.refresh_from_db()

        with (
            self.settings(TRACKER_PAYPAL_ALLOW_OLD_IPN_FORMAT=True),
            self.assertTrackerLogs(3, 'paypal'),
        ):
            self.assertDonation(
                task,
                'doe@example.com',
                dict(custom=f'{self.donation.id}:feedbeef'),
                matches=False,
            )

    def test_flagged(self, task):
        with self.assertTrackerLogs(2, 'paypal'):
            self.assertDonation(
                task, 'doe@example.com', dict(flag=True), transactionstate='FLAGGED'
            )

    def test_invalid_signature(self, task):
        custom = self.donation.paypal_signature.split(':', maxsplit=2)
        custom[2] = util.transpose(custom[2])

        with self.assertTrackerLogs(3, 'paypal'):
            self.assertDonation(
                task, 'doe@example.com', dict(custom=':'.join(custom)), matches=False
            )

    def test_signature_mismatch(self, task):
        custom = self.donation.paypal_signature.split(':', maxsplit=2)
        custom[1] = str(self.donation.id + 1)

        with self.assertTrackerLogs(3, 'paypal'):
            self.assertDonation(
                task, 'doe@example.com', dict(custom=':'.join(custom)), matches=False
            )

    def test_use_celery(self, task):
        with self.settings(TRACKER_HAS_CELERY=True):
            self.assertDonation(task, 'doe@example.com', {})

    def test_old_ipn(self, task):
        ipn = create_ipn(
            self.donation, 'doe@example.com', custom=f'{self.donation.id}:deadbeef'
        )

        with self.assertTrackerLogs(4, 'paypal'):
            self.assertDonation(
                task,
                'doe@example.com',
                dict(custom=f'{self.donation.id}:deadbeef'),
                matches=False,
            )
            self.assertIsNone(paypalutil.get_ipn_donation(ipn))

        with self.assertTrackerLogs(0):
            with self.settings(TRACKER_PAYPAL_ALLOW_OLD_IPN_FORMAT=True):
                self.assertDonation(
                    task,
                    'doe@example.com',
                    dict(custom=f'{self.donation.id}:deadbeef'),
                )

            self.assertEqual(
                self.donation, paypalutil.get_ipn_donation(ipn, allow_old_format=True)
            )

        with self.assertTrackerLogs(1, 'paypal'):
            # pathological, donation exists but wrong domain
            self.donation.domain = 'CHIPIN'
            self.donation.save()
            self.assertIsNone(paypalutil.get_ipn_donation(ipn, allow_old_format=True))

        ipn.custom = f'{self.donation.id + 1}:deadbeef'

        with self.assertTrackerLogs(1, 'paypal'):
            # pathological, donation does not exist
            self.assertIsNone(paypalutil.get_ipn_donation(ipn, allow_old_format=True))

    def test_really_old_ipn(self, task):
        # extremely unlikely that IPNs from 2013 are hitting the endpoint, but manually processing them should still
        # work
        ipn = create_ipn(
            self.donation, 'doe@example.com', custom=str(self.donation.event_id)
        )
        self.donation.domainId = ipn.txn_id
        self.donation.save()

        with self.assertTrackerLogs(0):
            self.assertEqual(
                self.donation, paypalutil.get_ipn_donation(ipn, allow_old_format=True)
            )

        self.donation.domainId = reversed(ipn.txn_id)
        self.donation.save()
        with self.assertTrackerLogs(1, 'paypal'):
            self.assertIsNone(paypalutil.get_ipn_donation(ipn, allow_old_format=True))
        task.assert_not_called()

    def test_blank_custom_field(self, task):
        # if a recipient has their IPN callback set to the tracker then ALL transactions will hit the IPN endpoint,
        # so ensure those don't explode

        with self.assertTrackerLogs(3, 'paypal'):
            self.assertDonation(task, 'doe@example.com', dict(custom=''), matches=False)

    def test_locked_event(self, task):
        self.event.locked = True
        self.event.save()

        self.assertDonation(task, 'doe@example.com', {}, matches=True, changes=False)
