from decimal import Decimal

import tracker.forms as forms
from django.test import TransactionTestCase


class TestDonorNameAssignment(TransactionTestCase):

    def testAliasAnonToVisibilityAnon(self):
        data = {
            'amount': Decimal('5.00'),
            'requestedvisibility': 'ALIAS',
            'requestedalias': 'Anonymous', }
        form = forms.DonationEntryForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['requestedvisibility'], 'ANON')
        self.assertFalse(bool(form.cleaned_data['requestedalias']))
