import datetime

from django.contrib.auth.models import Permission

from tracker import models
from tracker.api.serializers import BidSerializer

from ..test_bid import TestBidBase
from ..util import APITestCase


class TestBidViewSet(TestBidBase, APITestCase):
    model_name = 'bid'

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.super_user)

    def test_detail(self):
        serialized = BidSerializer(self.opened_parent_bid, tree=True)
        data = self.get_detail(self.opened_parent_bid)
        self.assertEqual(data, serialized.data)
        serialized = BidSerializer(self.chain_top, tree=True)
        data = self.get_detail(self.chain_top)
        self.assertEqual(data, serialized.data)

    def test_hidden_detail(self):
        with self.subTest('user with permission'):
            self.hidden_parent_bid.refresh_from_db()
            serialized = BidSerializer(
                self.hidden_parent_bid,
                include_hidden=True,
                tree=True,
                with_permissions=('tracker.view_hidden_bid',),
            )
            data = self.get_detail(self.hidden_parent_bid)
            self.assertEqual(data, serialized.data)

        with self.subTest('user without permission'):
            self.client.force_authenticate(user=None)
            self.get_detail(self.hidden_parent_bid, status_code=404)

    def test_list(self):
        with self.subTest('authenticated'):
            with self.subTest('normal list'):
                serialized = BidSerializer(
                    models.Bid.objects.filter(event=self.event).public(), many=True
                )
                data = self.get_list(kwargs={'event_pk': self.event.pk})
                self.assertEqual(data['results'], serialized.data)

            with self.subTest('feeds'):
                for feed in ['open', 'closed']:
                    with self.subTest(feed):
                        serialized = BidSerializer(
                            getattr(
                                models.Bid.objects.filter(event=self.event), feed
                            )(),
                            many=True,
                        )
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                        )
                        self.assertEqual(data['results'], serialized.data)

                # current is a bit more detailed
                with self.subTest('current'):
                    opened_bid = BidSerializer(self.opened_bid)
                    # challenge is pinned, always shows up regardless of parameters
                    challenge = BidSerializer(self.challenge)
                    data = self.get_list(
                        kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                        data={'now': self.run.starttime},
                    )
                    self.assertV2ModelPresent(opened_bid.data, data['results'])
                    self.assertV2ModelPresent(challenge.data, data['results'])
                    data = self.get_list(
                        kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                        data={'now': self.run.endtime + datetime.timedelta(seconds=1)},
                    )
                    self.assertV2ModelNotPresent(opened_bid.data, data['results'])
                    self.assertV2ModelPresent(challenge.data, data['results'])
                    # need `min_runs` or we'll just get the run anyway
                    data = self.get_list(
                        kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                        data={
                            'min_runs': 0,
                            'now': self.run.starttime - datetime.timedelta(minutes=60),
                            'delta': 30,
                        },
                    )
                    self.assertV2ModelNotPresent(opened_bid.data, data['results'])
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
                            many=True,
                        )
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                        )
                        self.assertEqual(data['results'], serialized.data)

        with self.subTest('anonymous'):
            self.client.force_authenticate(user=None)

            with self.subTest('normal feeds without permission'):
                self.get_list(
                    kwargs={'event_pk': self.event.pk},
                )
                for feed in ['open', 'closed', 'current']:
                    with self.subTest(feed):
                        self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                        )

            with self.subTest('hidden feeds without permission'):
                for feed in ['pending', 'all']:
                    with self.subTest(feed):
                        self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                            status_code=403,
                        )

    def test_tree(self):
        with self.subTest('normal tree'):
            serialized = BidSerializer(
                models.Bid.objects.filter(event=self.event, level=0).public(),
                many=True,
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
                tree=True,
            )
            data = self.get_noun(
                'tree',
                kwargs={'event_pk': self.event.pk, 'feed': 'all'},
            )
            self.assertEqual(data['results'], serialized.data)

        with self.subTest('hidden tree without permission'):
            self.get_noun(
                'tree',
                kwargs={'event_pk': self.event.pk, 'feed': 'all'},
                user=None,
                status_code=403,
            )

    def test_create(self):
        with self.subTest('attach to event'):
            data = self.post_new(data={'name': 'New Event Bid', 'event': self.event.pk})
            serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
            self.assertEqual(data, serialized.data)

        with self.subTest('attach to locked event with permission'):
            data = self.post_new(
                data={'name': 'New Locked Event Bid', 'event': self.locked_event.pk},
            )
            serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
            self.assertEqual(data, serialized.data)

        with self.subTest('attach to speedrun'):
            data = self.post_new(
                data={'name': 'New Run Bid', 'speedrun': self.run.pk},
            )
            serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
            self.assertEqual(data, serialized.data)

        with self.subTest('attach to locked speedrun with permission'):
            data = self.post_new(
                data={'name': 'New Locked Run Bid', 'speedrun': self.locked_run.pk},
            )
            serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
            self.assertEqual(data, serialized.data)

        with self.subTest('attach to parent'):
            data = self.post_new(
                data={'name': 'New Child', 'parent': self.opened_parent_bid.pk},
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

        with self.subTest('attach to locked parent with permission'):
            data = self.post_new(
                data={'name': 'New Locked Child', 'parent': self.locked_parent_bid.pk},
            )
            serialized = BidSerializer(models.Bid.objects.get(pk=data['id']))
            self.assertEqual(data, serialized.data)

        with self.subTest('attach to nonsense'):

            self.post_new(
                data={'name': 'Nonsense Bid', 'event': 'foo'}, status_code=400
            )
            data = self.post_new(
                data={'name': 'Nonsense Bid', 'speedrun': 'bar'},
                status_code=400,
            )
            data = self.post_new(
                data={'name': 'Nonsense Bid', 'parent': 'baz'},
                status_code=400,
            )

        with self.subTest('model validation'):
            # smoke test, don't want to repeat all the validation rules here
            data = self.post_new(
                data={
                    'name': 'Nonsense Repeat Bid',
                    'event': self.event.pk,
                    'goal': 500,
                    'repeat': 12,
                },
                status_code=400,
            )

        self.client.force_authenticate(user=self.add_user)

        with self.subTest('require top level permission for bids without parents'):
            self.post_new(
                data={'name': 'New Event Bid 2', 'event': self.event.pk},
                status_code=403,
            )

            self.post_new(
                data={
                    'name': 'New Child 2',
                    'parent': self.opened_parent_bid.pk,
                },
                status_code=201,
            )

        with self.subTest('require locked permission'):
            self.add_user.user_permissions.add(
                Permission.objects.get(codename='top_level_bid')
            )
            # TODO: maybe make a separate user for this
            del self.add_user._perm_cache
            del self.add_user._user_perm_cache

            self.post_new(
                data={
                    'name': 'New Locked Event Bid 2',
                    'event': self.locked_event.pk,
                },
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
        with self.subTest('can edit locked bid with permission'):
            data = self.patch_detail(
                self.locked_challenge, data={'name': 'Locked Updated'}
            )
            self.assertEqual(data['name'], 'Locked Updated')

        self.client.force_authenticate(user=self.add_user)

        with self.subTest('can edit top level bids'):
            data = self.patch_detail(
                self.opened_parent_bid,
                data={'name': 'Opened Parent Updated'},
            )
            self.assertEqual(data['name'], 'Opened Parent Updated')

        with self.subTest('should not be able to change parent'):
            self.patch_detail(
                self.opened_bid,
                data={'parent': self.opened_parent_bid.pk},
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
                data={'event': self.locked_event.pk},  # same parent
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
                data={'name': 'Opened Parent Updated Anonymous'},  # different parent
                status_code=403,
                user=None,
            )


class TestBidSerializer(TestBidBase, APITestCase):
    def _format_bid(self, bid, *, child=False, skip_children=False):
        data = {
            'type': 'bid',
            'id': bid.id,
            'name': bid.name,
            'state': bid.state,
            'description': bid.description,
            'shortdescription': bid.shortdescription,
            'total': bid.total,
            'count': bid.count,
            'istarget': bid.istarget,
            'revealedtime': bid.revealedtime,
            'level': bid.level,
        }
        if not child:
            data = {
                **data,
                'event': bid.event_id,
                'speedrun': bid.speedrun_id,
                'parent': bid.parent_id,
                'goal': bid.goal,
                'chain': bid.chain,
                'pinned': bid.pinned,
            }
            if not bid.chain:
                data = {
                    **data,
                    'repeat': bid.repeat,
                    'allowuseroptions': bid.allowuseroptions,
                }
        if bid.allowuseroptions:
            data = {**data, 'option_max_length': bid.option_max_length}
        if bid.chain:
            data = {
                **data,
                'goal': bid.goal,
                'chain_threshold': bid.chain_threshold,
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

        with self.subTest('child bid'):
            serialized = BidSerializer(self.opened_bid, tree=True)
            self.assertV2ModelPresent(
                self._format_bid(self.opened_bid), serialized.data
            )
