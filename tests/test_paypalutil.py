from django.test import TestCase

from paypal.standard.ipn.models import PayPalIPN

from tracker import paypalutil

class TestVerifyIPNRecipientEmail(TestCase):
    def test_match_is_okay(self):
        ipn = PayPalIPN(business='Charity@example.com')
        paypalutil.verify_ipn_recipient_email(ipn, 'charity@example.com')

        ipn = PayPalIPN(receiver_email='ChArItY@example.com')
        paypalutil.verify_ipn_recipient_email(ipn, 'charity@example.com')

    def test_mismatch_raises_exception(self):
        ipn = PayPalIPN(business='notthecharity@example.com')
        with self.assertRaises(paypalutil.SpoofedIPNException):
            paypalutil.verify_ipn_recipient_email(ipn, 'charity@example.com')

        ipn = PayPalIPN(receiver_email='notthecharity@example.com')
        with self.assertRaises(paypalutil.SpoofedIPNException):
            paypalutil.verify_ipn_recipient_email(ipn, 'charity@example.com')
