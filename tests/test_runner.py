from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

import tracker.models as models


class TestRunner(TransactionTestCase):
    def test_name_case_insensitivity(self):
        runner = models.Runner.objects.create(name='lowercase')
        runner.full_clean()  # does not trigger itself
        with self.assertRaises(ValidationError):
            models.Runner(name='LOWERCASE').full_clean()
