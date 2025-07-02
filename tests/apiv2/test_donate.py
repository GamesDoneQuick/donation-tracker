from decimal import Decimal

from django.contrib.auth.models import Permission
from django.core.signing import Signer

from tests import randgen
from tests.util import APITestCase
from tracker import models, settings
from tracker.api.serializers import DonationSerializer


class TestDonate(APITestCase):
    def setUp(self):
        super().setUp()
        self.opened_challenge = models.Bid.objects.create(
            event=self.event, name='Challenge', goal=1000, istarget=True, state='OPENED'
        )
        self.closed_challenge = models.Bid.objects.create(
            event=self.event,
            name='Past Challenge',
            goal=1000,
            istarget=True,
            state='CLOSED',
        )
        self.opened_choice = models.Bid.objects.create(
            event=self.event,
            name='Color',
            state='OPENED',
            istarget=False,
        )
        self.opened_parent = models.Bid.objects.create(
            event=self.event,
            name='Name',
            allowuseroptions=True,
            option_max_length=12,
            state='OPENED',
        )
        self.existing_name = models.Bid.objects.create(
            parent=self.opened_parent, name='John Halo', istarget=True
        )
        self.pending_name = models.Bid.objects.create(
            event=self.event, name='Spyro', istarget=True, state='PENDING'
        )
        self.closed_parent = models.Bid.objects.create(
            event=self.event, name='Past Name', allowuseroptions=True, state='CLOSED'
        )
        self.add_user.user_permissions.add(
            Permission.objects.get(name='Can add donation')
        )
        self.donor = randgen.generate_donor(self.rand)
        self.donor.save()

    def test_donate(self):
        valid = {
            'amount': 10,
            'event': self.event.id,
            'bids': [
                {'parent': self.opened_parent.id, 'name': 'Whomp', 'amount': 1},
                {
                    'parent': self.opened_parent.id,
                    'name': self.pending_name.name,
                    'amount': 1,
                },
                {'id': self.opened_challenge.id, 'amount': 1},
                {'id': self.existing_name.id, 'amount': 1},
            ],
            'comment': '',
            'email_optin': False,
            'requested_alias': '',
            'requested_email': '',
            'domain': 'PAYPAL',
        }

        with self.subTest('error cases'), self.saveSnapshot():
            with self.subTest('blank'):
                self.post_new(
                    data={},
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={
                        'amount': 'required',
                        'bids': 'required',
                        'comment': 'required',
                        'email_optin': 'required',
                        'event': 'required',
                        'requested_alias': 'required',
                        'requested_email': 'required',
                    },
                )

            with self.subTest('invalid event'):
                self.post_new(
                    data={**valid, 'event': 500, 'bids': []},
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'event': 'invalid'},
                )

            with self.subTest('archived event'):
                self.post_new(
                    data={**valid, 'event': self.archived_event.id, 'bids': []},
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'event': 'invalid'},
                )

            with self.subTest('amount too low'):
                self.post_new(
                    data={
                        **valid,
                        'amount': float(self.event.minimumdonation / 2),
                        'bids': [],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'amount': 'invalid'},
                )

            with self.subTest('amount too high'):
                self.post_new(
                    data={
                        **valid,
                        'amount': float(settings.TRACKER_PAYPAL_MAXIMUM_AMOUNT + 1),
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'amount': 'invalid'},
                )

            # FIXME: permission error instead?
            with self.subTest('local without donor'):
                self.post_new(
                    data={**valid, 'domain': 'LOCAL'},
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'domain': 'invalid'},
                )

            with self.subTest('other domain'):
                self.post_new(
                    data={**valid, 'domain': 'CHIPIN'},
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'domain': 'invalid'},
                )

            with self.subTest('invalid bid'):
                self.post_new(
                    data={**valid, 'bids': [{'id': 500, 'amount': 1}]},
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': 'invalid'},
                )

            with self.subTest('wrong event for bid'):
                self.post_new(
                    data={
                        **valid,
                        'event': self.blank_event.id,
                        'bids': [{'id': self.opened_challenge.id, 'amount': 1}],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': 'invalid'},
                )

                self.post_new(
                    data={
                        **valid,
                        'event': self.blank_event.id,
                        'bids': [
                            {'parent': self.opened_parent.id, 'name': 'a', 'amount': 1}
                        ],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': 'invalid'},
                )

            with self.subTest('closed bids'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [{'id': self.closed_challenge.id, 'amount': 1}],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': {'id': 'invalid'}},
                )

                self.post_new(
                    data={
                        **valid,
                        'bids': [
                            {'parent': self.closed_parent.id, 'name': 'a', 'amount': 1}
                        ],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': {'parent': 'invalid'}},
                )

            with self.subTest('suggestion without name'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [{'parent': self.opened_parent.id, 'amount': 1}],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': {'name': 'invalid'}},
                )

            with self.subTest('suggestion on choice without suggestions'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [{'parent': self.opened_choice.id, 'amount': 1}],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': {'parent': 'invalid'}},
                )

            with self.subTest('bid on parent instead of option'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [{'id': self.opened_choice.id, 'amount': 1}],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': {'id': 'invalid'}},
                )

            with self.subTest('parent with target'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [
                            {
                                'id': self.opened_challenge.id,
                                'parent': self.opened_choice.id,
                                'amount': 1,
                            }
                        ],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={
                        'bids': {'id': 'invalid', 'parent': 'invalid'}
                    },
                )

            with self.subTest('name with target'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [
                            {
                                'id': self.opened_choice.id,
                                'name': 'a',
                                'amount': 1,
                            }
                        ],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': {'id': 'invalid', 'name': 'invalid'}},
                )

            with self.subTest('bids higher than maximum'):
                self.post_new(
                    data={**valid, 'bids': [{'amount': valid['amount'] + 1}]},
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'amount': 'invalid'},
                )

                self.post_new(
                    data={
                        **valid,
                        'bids': [{'amount': valid['amount']}, {'amount': 1}],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'amount': 'invalid'},
                )

            with self.subTest('new suggestion too long'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [
                            {
                                'parent': self.opened_parent.id,
                                'name': 'a' * 100,
                                'amount': 1,
                            }
                        ],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': 'invalid'},
                )

            with self.subTest('duplicate target'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [
                            {'id': self.opened_challenge.id, 'amount': 1},
                            {'id': self.opened_challenge.id, 'amount': 1},
                        ],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': 'invalid'},
                )

            with self.subTest('duplicate suggestion'):
                self.post_new(
                    data={
                        **valid,
                        'bids': [
                            {
                                'parent': self.opened_parent.id,
                                'name': 'foobar',
                                'amount': 1,
                            },
                            {
                                'parent': self.opened_parent.id,
                                'name': 'foobar',
                                'amount': 1,
                            },
                        ],
                    },
                    status_code=400,
                    model_name='donate',
                    expected_error_codes={'bids': 'invalid'},
                )

        with self.subTest('happy path'), self.saveSnapshot():
            response = self.post_new(data=valid, model_name='donate')

            response = self.client.post(response['confirm_url'])

            # creates the donation and sends the payload via the form

            donation = models.Donation.objects.first()
            self.assertTemplateUsed(response, 'tracker/paypal_redirect.html')
            form_data = response.context['form'].initial
            self.assertEqual(Decimal(form_data['amount']), donation.amount)
            custom = Signer(
                salt=str(donation.amount.quantize(Decimal('0.00')))
            ).unsign_object(form_data['custom'].split(':', maxsplit=2)[2])
            self.assertEqual(custom['id'], donation.id)

        with self.subTest('create local'), self.saveSnapshot():
            response = self.post_new(
                data={
                    **valid,
                    # FIXME: what to do about hidden bids?
                    'bids': [],
                    'domain': 'LOCAL',
                    'donor_id': self.donor.id,
                },
                model_name='donate',
                status_code=201,
                user=self.add_user,
            )
            donation = models.Donation.objects.get(id=response['id'])
            self.assertV2ModelPresent(DonationSerializer(donation).data, response)
            self.assertEqual(donation.donor, self.donor)

            response = self.post_new(
                data={
                    **valid,
                    # FIXME: what to do about hidden bids?
                    'bids': [],
                    'domain': 'LOCAL',
                    'donor_email': self.donor.email,
                },
                model_name='donate',
                status_code=201,
                user=self.add_user,
            )
            donation = models.Donation.objects.get(id=response['id'])
            self.assertV2ModelPresent(DonationSerializer(donation).data, response)
            self.assertEqual(donation.donor, self.donor)

        with self.subTest('create twitch'), self.saveSnapshot():
            response = self.post_new(
                data={
                    **valid,
                    # FIXME: what to do about hidden bids?
                    'bids': [],
                    'domain': 'TWITCH',
                    'requested_alias': 'Kappa',
                    'donor_twitch_id': 12345678,
                },
                model_name='donate',
                status_code=201,
                user=self.add_user,
            )
            donation = models.Donation.objects.get(id=response['id'])
            self.assertV2ModelPresent(DonationSerializer(donation).data, response)
            self.assertEqual(donation.donor.twitch_id, 12345678)
            self.assertEqual(donation.donor.email, '12345678@users.twitch.tv.fake')
            self.assertEqual(donation.requestedalias, 'Kappa')
            self.assertEqual(donation.requestedvisibility, 'ALIAS')
            self.assertEqual(donation.transactionstate, 'COMPLETED')
