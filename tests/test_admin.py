from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.auth import get_user_model

from tracker.models import Donor

User = get_user_model()


class MergeDonorsViewTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(
            'superuser',
            'super@example.com',
            'password',
        )
        self.client.login(username='superuser', password='password')

    def tearDown(self):
        self.client.logout()

    def test_get_loads(self):
        d1 = Donor.objects.create()
        d2 = Donor.objects.create()
        ids = "{},{}".format(d1.pk, d2.pk)

        response = self.client.get(
            reverse('admin:merge_donors'), {'objects': ids})
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Select which donor to use as the template")
