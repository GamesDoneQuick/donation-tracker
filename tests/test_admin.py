import random

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.urls import reverse

from tracker import randgen, models

User = get_user_model()


class MergeDonorsViewTests(TestCase):
    def setUp(self):
        User.objects.create_superuser(
            'superuser', 'super@example.com', 'password',
        )
        self.client.login(username='superuser', password='password')

    def tearDown(self):
        self.client.logout()

    def test_get_loads(self):
        d1 = models.Donor.objects.create()
        d2 = models.Donor.objects.create()
        ids = '{},{}'.format(d1.pk, d2.pk)

        response = self.client.get(reverse('admin:merge_donors'), {'objects': ids})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select which donor to use as the template')


class ProcessDonationsTest(TestCase):
    def setUp(self):
        self.rand = random.Random(None)
        self.superuser = User.objects.create_superuser(
            'superuser', 'super@example.com', 'password',
        )
        self.processor = User.objects.create(username='processor', is_staff=True)
        self.processor.user_permissions.add(
            Permission.objects.get(name='Can change donor'),
            Permission.objects.get(name='Can change donation'),
        )
        self.head_processor = User.objects.create(
            username='head_processor', is_staff=True
        )
        self.head_processor.user_permissions.add(
            Permission.objects.get(name='Can change donor'),
            Permission.objects.get(name='Can change donation'),
            Permission.objects.get(name='Can send donations to the reader'),
        )
        self.event = randgen.build_random_event(self.rand)
        self.session = self.client.session
        self.session['admin-event'] = self.event.id
        self.session.save()

    def test_no_event_selected_non_head(self):
        del self.session['admin-event']
        self.session.save()
        self.client.force_login(self.processor)
        response = self.client.get(reverse('admin:process_donations'))
        self.assertEqual(response.context['user_can_approve'], False)
        self.assertEqual(response.status_code, 200)

    def test_no_event_selected_with_head(self):
        del self.session['admin-event']
        self.session.save()
        self.client.force_login(self.head_processor)
        response = self.client.get(reverse('admin:process_donations'))
        self.assertEqual(response.context['user_can_approve'], True)
        self.assertEqual(response.status_code, 200)

    def test_one_step_screening(self):
        self.client.force_login(self.processor)
        response = self.client.get(reverse('admin:process_donations'))
        self.assertEqual(response.context['user_can_approve'], True)
        self.assertEqual(response.status_code, 200)

    def test_two_step_screening_non_head(self):
        self.event.use_one_step_screening = False
        self.event.save()
        self.client.force_login(self.processor)
        response = self.client.get(reverse('admin:process_donations'))
        self.assertEqual(response.context['user_can_approve'], False)
        self.assertEqual(response.status_code, 200)

    def test_two_step_screening_with_head(self):
        self.event.use_one_step_screening = False
        self.event.save()
        self.client.force_login(self.head_processor)
        response = self.client.get(reverse('admin:process_donations'))
        self.assertEqual(response.context['user_can_approve'], True)
        self.assertEqual(response.status_code, 200)


class TestAdminViews(TestCase):
    # smoke tests for other views that don't have more detailed tests yet
    def setUp(self):
        self.rand = random.Random(None)
        self.superuser = User.objects.create_superuser(
            'superuser', 'super@example.com', 'password',
        )
        self.event = randgen.build_random_event(self.rand)
        self.session = self.client.session
        self.session['admin-event'] = self.event.id
        self.session.save()

    def test_read_donations(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:read_donations'))
        self.assertEqual(response.status_code, 200)

    def test_process_donations(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:process_donations'))
        self.assertEqual(response.status_code, 200)

    def test_process_prize_submissions(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:process_prize_submissions'))
        self.assertEqual(response.status_code, 200)

    def test_merge_bids(self):
        self.client.force_login(self.superuser)
        randgen.generate_runs(self.rand, self.event, 5)
        randgen.generate_bids(self.rand, self.event, 10)
        response = self.client.get(
            reverse('admin:merge_bids'),
            {'objects': ','.join(str(b.id) for b in models.Bid.objects.all())},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Select which bid to use as the template')

    def test_process_pending_bids(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:process_pending_bids'))
        self.assertEqual(response.status_code, 200)

    def test_automail_prize_contributors(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:automail_prize_contributors'))
        self.assertEqual(response.status_code, 200)

    def test_automail_prize_winners(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:automail_prize_winners'))
        self.assertEqual(response.status_code, 200)

    def test_draw_prize_winners(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:draw_prize_winners'))
        self.assertEqual(response.status_code, 200)

    def test_automail_prize_accept_notifications(self):
        self.client.force_login(self.superuser)
        response = self.client.get(reverse('admin:automail_prize_accept_notifications'))
        self.assertEqual(response.status_code, 200)

    def test_automail_prize_shipping_notifications(self):
        self.client.force_login(self.superuser)
        response = self.client.get(
            reverse('admin:automail_prize_shipping_notifications')
        )
        self.assertEqual(response.status_code, 200)
