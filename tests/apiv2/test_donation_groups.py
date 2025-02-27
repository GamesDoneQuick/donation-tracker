from django.urls import reverse

from tests.util import APITestCase
from tracker import models
from tracker.api.views.donation_groups import AbstractTagSerializer


class TestDonationGroups(APITestCase):
    model_name = 'donationgroup'
    serializer_class = AbstractTagSerializer
    extra_serializer_kwargs = {'model': models.DonationGroup}
    add_user_permissions = ['delete_donationgroup']

    def test_update_and_destroy(self):
        response = self.client.put(
            reverse(self._get_viewname(self.model_name, 'detail'), kwargs={'pk': 'foo'})
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.delete(
            reverse(self._get_viewname(self.model_name, 'detail'), kwargs={'pk': 'foo'})
        )
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.add_user)

        url = reverse(
            self._get_viewname(self.model_name, 'detail'), kwargs={'pk': 'foo'}
        )

        with self.saveSnapshot(), self.assertLogsChanges(1), self.process_snapshot(
            'PUT', url
        ) as snapshot:
            response = self.client.put(url)
            snapshot.process_response(response)
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.data, 'foo')

        with self.assertLogsChanges(0):
            # no-op
            response = self.client.put(url)
            self.assertEqual(response.status_code, 200)

        with self.saveSnapshot(), self.assertLogsChanges(1), self.process_snapshot(
            'DELETE', url
        ) as snapshot:
            response = self.client.delete(url)
            snapshot.process_response(response)
            self.assertEqual(response.status_code, 204)

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
