from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

import tracker.models as models


class TestHeadset(TransactionTestCase):
    def setUp(self):
        self.headset = models.Headset.objects.create(name='lowercase')

    def test_name_case_insensitivity(self):
        self.headset.full_clean()  # does not trigger itself
        with self.assertRaises(ValidationError):
            models.Headset(name='LOWERCASE').full_clean()

    def test_natural_key(self):
        self.assertEqual(
            models.Headset.objects.get_by_natural_key(*self.headset.natural_key()),
            self.headset,
        )
