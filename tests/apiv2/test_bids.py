import datetime

from django.contrib.auth.models import Permission, User

from tracker import models
from tracker.api.serializers import BidSerializer

from ..test_bid import TestBidBase
from ..util import APITestCase


class TestBidViewSet(TestBidBase, APITestCase):
    model_name = 'bid'
    add_user_permissions = ['top_level_bid']
    serializer_class = BidSerializer

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.locked_user)

        # to test toplevel permission
        self.limited_user = User.objects.create(username='limited_user')
        self.limited_user.user_permissions.add(
            Permission.objects.get(codename='add_bid'),
            Permission.objects.get(codename='change_bid'),
        )
        self.view_hidden_user = User.objects.create(username='view_hidden_user')
        self.view_hidden_user.user_permissions.add(
            Permission.objects.get(codename='view_hidden_bid')
        )

    def test_fetch(self):
        with self.saveSnapshot():
            with self.subTest('detail'):
                serialized = BidSerializer(self.opened_parent_bid, tree=True)
                data = self.get_detail(self.opened_parent_bid)
                self.assertEqual(data, serialized.data)
                serialized = BidSerializer(self.chain_top, tree=True)
                data = self.get_detail(self.chain_top)
                self.assertEqual(data, serialized.data)

                with self.subTest('nested'):
                    serialized = BidSerializer(
                        self.opened_parent_bid, event_pk=self.event.id, tree=True
                    )
                    data = self.get_detail(
                        self.opened_parent_bid, kwargs={'event_pk': self.event.id}
                    )
                    self.assertEqual(data, serialized.data)
                with self.subTest('hidden'):
                    self.hidden_parent_bid.refresh_from_db()
                    serialized = BidSerializer(
                        self.hidden_parent_bid,
                        include_hidden=True,
                        tree=True,
                        with_permissions=('tracker.view_hidden_bid',),
                    )
                    data = self.get_detail(self.hidden_parent_bid)
                    self.assertEqual(data, serialized.data)
            with self.subTest('list'):
                serialized = BidSerializer(
                    models.Bid.objects.filter(event=self.event).public(),
                    event_pk=self.event.id,
                    many=True,
                )
                data = self.get_list(kwargs={'event_pk': self.event.pk})
                self.assertEqual(data['results'], serialized.data)

                with self.subTest('normal tree'):
                    serialized = BidSerializer(
                        models.Bid.objects.filter(event=self.event, level=0).public(),
                        many=True,
                        event_pk=self.event.id,
                        tree=True,
                    )
                    data = self.get_noun('tree', kwargs={'event_pk': self.event.pk})
                    self.assertEqual(data['results'], serialized.data)

                with self.subTest('hidden tree'):
                    serialized = BidSerializer(
                        models.Bid.objects.filter(event=self.event, level=0),
                        include_hidden=True,
                        with_permissions=('tracker.view_hidden_bid',),
                        many=True,
                        event_pk=self.event.id,
                        tree=True,
                    )
                    data = self.get_noun(
                        'tree',
                        kwargs={'event_pk': self.event.pk, 'feed': 'all'},
                    )
                    self.assertEqual(data['results'], serialized.data)

            with self.subTest('feeds'):
                for feed in ['open', 'closed']:
                    with self.subTest(feed):
                        serialized = BidSerializer(
                            getattr(
                                models.Bid.objects.filter(event=self.event), feed
                            )(),
                            event_pk=self.event.id,
                            many=True,
                        )
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                        )
                        self.assertEqual(data['results'], serialized.data)

                # current is a bit more detailed
                with self.subTest('current'):
                    opened_bid = BidSerializer(self.opened_bid, event_pk=self.event.id)
                    # challenge is pinned, always shows up regardless of parameters
                    challenge = BidSerializer(self.challenge, event_pk=self.event.id)

                    with self.subTest('start of run'):
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                            data={'now': self.run.starttime},
                        )
                        self.assertV2ModelPresent(opened_bid.data, data['results'])
                        self.assertV2ModelPresent(challenge.data, data['results'])
                    with self.suppressSnapshot():
                        with self.subTest('end of run'):
                            data = self.get_list(
                                kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                                data={
                                    'now': self.run.endtime
                                    + datetime.timedelta(seconds=1)
                                },
                            )
                            self.assertV2ModelNotPresent(
                                opened_bid.data, data['results']
                            )
                            self.assertV2ModelPresent(challenge.data, data['results'])
                        # need `min_runs` or we'll just get the run anyway
                        with self.subTest('an hour ago'):
                            data = self.get_list(
                                kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                                data={
                                    'min_runs': 0,
                                    'now': self.run.starttime
                                    - datetime.timedelta(minutes=60),
                                    'delta': 30,
                                },
                            )
                            self.assertV2ModelNotPresent(
                                opened_bid.data, data['results']
                            )
                            self.assertV2ModelPresent(challenge.data, data['results'])

                        # pathological, but it tests max_runs
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                            data={'max_runs': 0, 'now': self.run.starttime},
                        )
                        self.assertV2ModelNotPresent(opened_bid.data, data['results'])
                        self.assertV2ModelPresent(challenge.data, data['results'])

                # hidden feeds
                for feed in ['pending', 'all']:
                    with self.subTest(feed):
                        serialized = BidSerializer(
                            getattr(
                                models.Bid.objects.filter(event=self.event), feed
                            )(),
                            include_hidden=True,
                            with_permissions=('tracker.view_hidden_bid',),
                            event_pk=self.event.id,
                            many=True,
                        )
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                        )
                        self.assertEqual(data['results'], serialized.data)

        with self.subTest('limited permissions'):
            self.get_list(data={'feed': 'all'}, user=self.view_hidden_user)
            self.get_detail(self.denied_bid)
            self.get_list(data={'feed': 'all'}, user=self.view_user)
            self.get_detail(self.denied_bid)

        with self.subTest('anonymous'):
            with self.subTest('normal feeds without permission'):
                self.get_list(
                    kwargs={'event_pk': self.event.pk},
                )
                for feed in ['open', 'closed', 'current']:
                    with self.subTest(feed):
                        self.get_list(
                            user=None,
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                        )

            with self.subTest('error cases'):
                with self.subTest('hidden feeds without permission'):
                    for feed in ['pending', 'all']:
                        with self.subTest(feed):
                            self.get_list(
                                kwargs={'event_pk': self.event.pk, 'feed': feed},
                                status_code=403,
                            )

                with self.subTest('hidden bid without permission'):
                    self.get_detail(self.hidden_parent_bid, status_code=404)

                with self.subTest('hidden tree without permission'):
                    self.get_noun(
                        'tree',
                        kwargs={'event_pk': self.event.pk, 'feed': 'all'},
                        status_code=403,
                    )

    def test_create(self):
        with self.saveSnapshot(), self.assertLogsChanges(4):
            # TODO: natural key tests
            with self.subTest('attach to event'):
                data = self.post_new(
                    data={'name': 'New Event Bid', 'event': self.event.pk}
                )
                serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
                self.assertEqual(data, serialized.data)

            with self.subTest('attach to parent'):
                data = self.post_new(
                    data={'name': 'New Child', 'parent': self.opened_parent_bid.pk},
                )
                serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
                self.assertEqual(data, serialized.data)

            with self.subTest('attach to speedrun'):
                data = self.post_new(
                    data={'name': 'New Run Bid', 'speedrun': self.run.pk},
                )
                serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
                self.assertEqual(data, serialized.data)

            with self.subTest('attach to chain'):
                data = self.post_new(
                    data={
                        'name': 'Chain Abyss',
                        'parent': self.chain_bottom.pk,
                        'goal': 50,
                    },
                )
                serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
                self.assertEqual(data, serialized.data)

        with self.subTest('attach to locked event with permission'):
            data = self.post_new(
                data={'name': 'New Locked Event Bid', 'event': self.locked_event.pk},
                user=self.locked_user,
            )
            serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
            self.assertEqual(data, serialized.data)

        with self.subTest('attach to locked speedrun with permission'):
            data = self.post_new(
                data={'name': 'New Locked Run Bid', 'speedrun': self.locked_run.pk},
            )
            serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
            self.assertEqual(data, serialized.data)

        with self.subTest('attach to locked parent with permission'):
            data = self.post_new(
                data={'name': 'New Locked Child', 'parent': self.locked_parent_bid.pk},
            )
            serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
            self.assertEqual(data, serialized.data)

        with self.subTest('error cases'):
            with self.subTest('attach to nonsense'):
                self.post_new(
                    data={'name': 'Nonsense Bid', 'event': 'foo'},
                    status_code=400,
                    expected_error_codes={'event': 'incorrect_type'},
                )
                self.post_new(
                    data={'name': 'Nonsense Bid', 'speedrun': 'bar'},
                    status_code=400,
                    expected_error_codes={'speedrun': 'incorrect_type'},
                )
                self.post_new(
                    data={'name': 'Nonsense Bid', 'parent': 'baz'},
                    status_code=400,
                    expected_error_codes={'parent': 'incorrect_type'},
                )

            with self.subTest('model validation'):
                # smoke test, don't want to repeat all the validation rules here
                self.post_new(
                    data={
                        'name': 'Nonsense Repeat Bid',
                        'event': self.event.pk,
                        'goal': 500,
                        'repeat': 12,
                        'istarget': True,
                    },
                    status_code=400,
                    expected_error_codes={'repeat': 'invalid'},
                )

            with self.subTest('require locked permission'):
                self.post_new(
                    data={
                        'name': 'New Locked Event Bid 2',
                        'event': self.locked_event.pk,
                    },
                    user=self.add_user,
                    status_code=403,
                )

                self.post_new(
                    data={
                        'name': 'New Locked Run Bid 2',
                        'speedrun': self.locked_run.pk,
                    },
                    status_code=403,
                )

                self.post_new(
                    data={
                        'name': 'New Locked Child 2',
                        'parent': self.locked_parent_bid.pk,
                    },
                    status_code=403,
                )

            with self.subTest('require top level permission for bids without parents'):
                self.post_new(
                    data={'name': 'New Event Bid 2', 'event': self.event.pk},
                    user=self.limited_user,
                    status_code=403,
                )

                self.post_new(
                    data={
                        'name': 'New Child 2',
                        'parent': self.opened_parent_bid.pk,
                    },
                    status_code=201,
                )

            with self.subTest('anonymous'):
                self.post_new(
                    data={
                        'name': 'New Child 3',
                        'parent': self.opened_parent_bid.pk,
                    },
                    status_code=403,
                    user=None,
                )

    def test_patch(self):
        with self.saveSnapshot(), self.assertLogsChanges(1):
            data = self.patch_detail(self.challenge, data={'name': 'Challenge Updated'})
            self.assertV2ModelPresent(self.challenge, data)

        with self.subTest(
            'can edit locked bid with permission'
        ), self.assertLogsChanges(1):
            data = self.patch_detail(
                self.locked_challenge, data={'name': 'Locked Updated'}
            )
            self.assertEqual(data['name'], 'Locked Updated')

        with self.subTest(
            'can edit top level bids even without creation permission'
        ), self.assertLogsChanges(1):
            data = self.patch_detail(
                self.opened_parent_bid,
                data={'name': 'Opened Parent Updated'},
                user=self.limited_user,
            )
            self.assertEqual(data['name'], 'Opened Parent Updated')

        with self.subTest('should not be able to change parent'):
            self.patch_detail(
                self.opened_bid,
                data={'parent': self.opened_parent_bid.pk},  # same parent, so no-op
            )

            self.patch_detail(
                self.opened_bid,
                data={'parent': self.closed_parent_bid.pk},
                status_code=400,
            )

        with self.subTest('should not be able to edit locked bid without permission'):
            self.patch_detail(
                self.locked_challenge,
                data={'name': 'Locked Updated Again'},
                status_code=403,
            )

        with self.subTest('should not be able to move to a locked event'):
            self.patch_detail(
                self.opened_parent_bid,
                data={'event': self.locked_event.pk},
                status_code=403,
            )
            self.patch_detail(
                self.opened_parent_bid,
                data={'speedrun': self.locked_run.pk},
                status_code=403,
            )

        with self.subTest('anonymous'):
            self.patch_detail(
                self.opened_parent_bid,
                data={'name': 'Opened Parent Updated Anonymous'},
                status_code=403,
                user=None,
            )


class TestBidSerializer(TestBidBase, APITestCase):
    def _format_bid(self, bid, *, with_event=True, child=False, skip_children=False):
        data = {
            'type': 'bid',
            'id': bid.id,
            'name': bid.name,
            'state': bid.state,
            'description': bid.description,
            'shortdescription': bid.shortdescription,
            'estimate': bid.estimate,
            'total': bid.total,
            'count': bid.count,
            'istarget': bid.istarget,
            'revealedtime': bid.revealedtime,
            'level': bid.level,
        }
        if not child:
            data = {
                **data,
                'speedrun': bid.speedrun_id,
                'parent': bid.parent_id,
                'goal': bid.goal,
                'chain': bid.chain,
                'pinned': bid.pinned,
            }
            if with_event:
                data['event'] = bid.event_id
            if not bid.chain:  # neither child nor chain
                data = {
                    **data,
                    'close_at': bid.close_at,
                    'post_run': bid.post_run,
                    'repeat': bid.repeat,
                    'allowuseroptions': bid.allowuseroptions,
                }
        if bid.allowuseroptions:
            data = {**data, 'option_max_length': bid.option_max_length}
        if bid.chain:
            data = {
                **data,
                'goal': bid.goal,
                'chain_goal': bid.chain_goal,
                'chain_remaining': bid.chain_remaining,
            }
            if bid.istarget and not skip_children:
                data['chain_steps'] = [
                    self._format_bid(chain, child=True)
                    for chain in bid.get_descendants()
                ]
        elif not (bid.istarget or skip_children):
            data['options'] = [
                self._format_bid(option, child=True) for option in bid.get_children()
            ]

        return data

    def test_single(self):
        with self.subTest('chained bid'):
            # TODO
            # serialized = BidSerializer(self.chain_top)
            # self.assertV2ModelPresent(self._format_bid(self.chain_top, tree=False), serialized.data)

            serialized = BidSerializer(self.chain_top, tree=True)
            self.assertV2ModelPresent(self._format_bid(self.chain_top), serialized.data)
            self.assertV2ModelPresent(
                self._format_bid(self.chain_middle, child=True),
                serialized.data['chain_steps'],
                partial=True,
            )
            self.assertV2ModelPresent(
                self._format_bid(self.chain_bottom, child=True),
                serialized.data['chain_steps'],
                partial=True,
            )
            serialized = BidSerializer(self.chain_middle, tree=True)
            self.assertV2ModelPresent(
                self._format_bid(self.chain_middle), serialized.data
            )
            serialized = BidSerializer(self.chain_bottom, tree=True)
            self.assertV2ModelPresent(
                self._format_bid(self.chain_bottom), serialized.data
            )

        with self.subTest('bid with options'):
            serialized = BidSerializer(self.opened_parent_bid, tree=True)
            self.assertV2ModelPresent(
                self._format_bid(self.opened_parent_bid, skip_children=True),
                serialized.data,
                partial=True,
            )
            self.assertV2ModelPresent(
                self._format_bid(self.opened_bid, child=True),
                serialized.data['options'],
            )
            with self.subTest(
                'should not include the hidden children unless specifically asked and the permission is included'
            ):
                self.assertV2ModelNotPresent(
                    self._format_bid(self.denied_bid, child=True),
                    serialized.data['options'],
                )
                self.assertV2ModelNotPresent(
                    self._format_bid(self.pending_bid, child=True),
                    serialized.data['options'],
                )

                serialized = BidSerializer(
                    self.opened_parent_bid,
                    tree=True,
                    include_hidden=True,
                    with_permissions=('tracker.view_hidden_bid',),
                )
                self.assertV2ModelPresent(
                    self._format_bid(self.denied_bid, child=True),
                    serialized.data['options'],
                )
                self.assertV2ModelPresent(
                    self._format_bid(self.pending_bid, child=True),
                    serialized.data['options'],
                )

        with self.subTest('hidden permissions checks'):
            for bid in [
                self.pending_bid,
                self.denied_bid,
                self.hidden_bid,
                self.hidden_parent_bid,
            ]:
                # smoke test for base case
                with self.assertRaises(AssertionError):
                    BidSerializer().to_representation(bid)

                # flag isn't enough, permission needs to be provided
                with self.assertRaises(AssertionError):
                    BidSerializer(include_hidden=True).to_representation(bid)

                # permission isn't enough, the flag needs to be specified too
                with self.assertRaises(AssertionError):
                    BidSerializer(
                        with_permissions='tracker.view_hidden_bid'
                    ).to_representation(bid)

                # any of the following permissions are sufficient
                for perm in [
                    'tracker.view_hidden_bid',
                    'tracker.view_bid',
                    'tracker.change_bid',
                ]:
                    BidSerializer(
                        include_hidden=True, with_permissions=perm
                    ).to_representation(bid)

        with self.subTest('child bid'):
            serialized = BidSerializer(self.opened_bid, tree=True)
            self.assertV2ModelPresent(
                self._format_bid(self.opened_bid), serialized.data
            )
