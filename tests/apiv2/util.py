from django.contrib.admin.models import LogEntry
from django.test.testcases import TransactionTestCase


class APITestCase(TransactionTestCase):
    # change_type is one of ADDITION, CHANGE, or DELETION from LogEntry
    def assertLogEntry(self, model_name: str, pk: int, change_type, message: str):
        entry = LogEntry.objects.get(
            content_type__model__iexact=model_name,
            action_flag=change_type,
            object_id=pk,
        )

        self.assertIsNotNone(entry)
        self.assertEqual(entry.change_message, message)
