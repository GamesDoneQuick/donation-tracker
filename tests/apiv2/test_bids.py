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
        self.client.force_authenticate(self.add_user)

        # to test toplevel permission
        self.limited_user = User.objects.create(username='limited_user')
        self.limited_user.user_permissions.add(
            Permission.objects.get(codename='add_bid'),
            Permission.objects.get(codename='change_bid'),
            Permission.objects.get(codename='view_bid'),
        )
        self.approval_user = User.objects.create(username='approval_user')
        self.approval_user.user_permissions.add(
            Permission.objects.get(codename='approve_bid'),
            Permission.objects.get(codename='view_bid'),
        )

    def _test_detail_fetch(
        self, bid, serializer_kwargs=None, url_kwargs=None, **kwargs
    ):
        serializer_kwargs = {**kwargs, **(serializer_kwargs or {})}
        url_kwargs = {**kwargs, **(url_kwargs or {})}
        with self.subTest('flat'):
            serialized = self._serialize_models(bid, **serializer_kwargs)
            data = self.get_detail(bid, kwargs=url_kwargs)
            self.assertV2ModelPresent(serialized, data)

        with self.subTest('tree'):
            serialized = self._serialize_models(bid, tree=True, **serializer_kwargs)
            data = self.get_noun('tree-detail', bid, kwargs=url_kwargs)
            self.assertV2ModelPresent(serialized, data)

    def test_fetch(self):
        with self.saveSnapshot():
            with self.subTest('detail'):
                self._test_detail_fetch(self.opened_parent_bid)
                self._test_detail_fetch(self.chain_top)

                with self.subTest('nested'):
                    self._test_detail_fetch(
                        self.opened_parent_bid, event_pk=self.event.id
                    )

                with self.subTest('hidden'):
                    self.hidden_parent_bid.refresh_from_db()
                    self._test_detail_fetch(
                        self.hidden_parent_bid,
                        serializer_kwargs=dict(
                            include_hidden=True, with_permissions=('tracker.view_bid',)
                        ),
                    )

                with self.suppressSnapshot(), self.subTest('draft'):
                    self._test_detail_fetch(self.draft_challenge)
                    self._test_detail_fetch(self.draft_challenge)

            with self.subTest('list'):
                serialized = self._serialize_models(
                    models.Bid.objects.filter(event=self.event).public(),
                    event_pk=self.event.id,
                    many=True,
                )
                data = self.get_list(kwargs={'event_pk': self.event.pk})
                self.assertExactV2Models(serialized, data)

                with self.subTest('normal tree'):
                    serialized = self._serialize_models(
                        models.Bid.objects.filter(event=self.event, level=0).public(),
                        many=True,
                        event_pk=self.event.id,
                        tree=True,
                    )
                    data = self.get_noun('tree', kwargs={'event_pk': self.event.pk})
                    self.assertExactV2Models(serialized, data)

                with self.subTest('hidden tree'):
                    serialized = self._serialize_models(
                        models.Bid.objects.filter(event=self.event, level=0),
                        include_hidden=True,
                        with_permissions=('tracker.view_bid',),
                        many=True,
                        event_pk=self.event.id,
                        tree=True,
                    )
                    data = self.get_noun(
                        'tree',
                        kwargs={'event_pk': self.event.pk, 'feed': 'all'},
                    )
                    self.assertExactV2Models(serialized, data)

                with self.suppressSnapshot(), self.subTest('draft list'):
                    serialized = BidSerializer(
                        models.Bid.objects.filter(event=self.draft_event),
                        with_permissions=('tracker.view_event',),
                        many=True,
                        event_pk=self.draft_event.id,
                    )
                    data = self.get_list(
                        kwargs={'event_pk': self.draft_event.pk},
                    )
                    self.assertExactV2Models(serialized.data, data)
                    serialized = BidSerializer(
                        models.Bid.objects.filter(event=self.draft_event),
                        with_permissions=('tracker.view_event',),
                        many=True,
                        event_pk=self.draft_event.id,
                        tree=True,
                    )
                    data = self.get_noun(
                        'tree',
                        kwargs={'event_pk': self.draft_event.pk},
                    )
                    self.assertExactV2Models(serialized.data, data)

            with self.subTest('feeds'):
                for feed in ['open', 'closed']:
                    with self.subTest(feed):
                        serialized = self._serialize_models(
                            getattr(
                                models.Bid.objects.filter(event=self.event), feed
                            )(),
                            event_pk=self.event.id,
                            many=True,
                        )
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                        )
                        self.assertExactV2Models(serialized, data)

                with self.subTest('current'):
                    with self.subTest('start of run'):
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                            data={'now': self.run.starttime},
                        )
                        self.assertV2ModelPresent(self.opened_bid, data)
                        self.assertV2ModelPresent(self.closed_bid, data)
                        self.assertV2ModelPresent(self.challenge, data)
                    with self.suppressSnapshot():
                        with self.subTest('end of run'):
                            data = self.get_list(
                                kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                                data={
                                    'now': self.run.endtime
                                    + datetime.timedelta(seconds=1)
                                },
                            )
                            self.assertV2ModelPresent(self.opened_bid, data)
                            self.assertV2ModelNotPresent(self.closed_bid, data)
                            self.assertV2ModelPresent(self.challenge, data)
                        with self.subTest('an hour ago'):
                            # tests the hour window
                            data = self.get_list(
                                kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                                data={
                                    'now': self.run.starttime
                                    - datetime.timedelta(hours=1),
                                },
                            )
                            self.assertV2ModelPresent(self.opened_bid, data)
                            self.assertV2ModelPresent(self.closed_bid, data)
                            self.assertV2ModelPresent(self.challenge, data)
                        with self.subTest('an hour ago and one second ago'):
                            data = self.get_list(
                                kwargs={'event_pk': self.event.pk, 'feed': 'current'},
                                data={
                                    'now': self.run.starttime
                                    - datetime.timedelta(minutes=60, seconds=1),
                                },
                            )
                            self.assertV2ModelPresent(self.opened_bid, data)
                            self.assertV2ModelNotPresent(self.closed_bid, data)
                            self.assertV2ModelPresent(self.challenge, data)

                # hidden feeds
                for feed in ['pending', 'all']:
                    with self.subTest(feed):
                        serialized = self._serialize_models(
                            getattr(
                                models.Bid.objects.filter(event=self.event), feed
                            )(),
                            include_hidden=True,
                            with_permissions=('tracker.view_bid',),
                            event_pk=self.event.id,
                            many=True,
                        )
                        data = self.get_list(
                            kwargs={'event_pk': self.event.pk, 'feed': feed},
                        )
                        self.assertExactV2Models(serialized, data)

        with self.subTest('limited permissions'):
            self.get_list(data={'feed': 'all'}, user=self.view_user)
            self.get_detail(self.denied_bid)

        with self.subTest('anonymous'):
            with self.subTest('does not include draft bids for full list'):
                data = self.get_list()
                self.assertV2ModelNotPresent(
                    self.draft_challenge,
                    data,
                )

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
                with self.subTest('tree on non-toplevel'):
                    for bid in models.Bid.objects.exclude(parent=None):
                        self.get_noun('tree-detail', bid, status_code=404)

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

                with self.subTest('draft event without permission'):
                    self.get_detail(self.draft_challenge, status_code=404)
                    self.get_noun(
                        'tree',
                        kwargs={'event_pk': self.draft_event.pk},
                        status_code=404,
                    )

    def test_create(self):
        with self.saveSnapshot(), self.assertLogsChanges(7):
            # TODO: natural key tests
            with self.subTest('attach to event'):
                data = self.post_new(
                    data={'name': 'New Event Bid', 'event': self.event.pk}
                )
                serialized = self._serialize_models(
                    models.Bid.objects.get(pk=data['id'])
                )
                self.assertEqual(data, serialized)

            with self.subTest('attach to parent'):
                data = self.post_new(
                    data={'name': 'New Child', 'parent': self.opened_parent_bid.pk},
                )
                serialized = self._serialize_models(
                    models.Bid.objects.get(pk=data['id'])
                )
                self.assertEqual(data, serialized)

            with self.subTest('attach to speedrun'):
                data = self.post_new(
                    data={'name': 'New Run Bid', 'speedrun': self.run.pk},
                )
                serialized = self._serialize_models(
                    models.Bid.objects.get(pk=data['id'])
                )
                self.assertEqual(data, serialized)

            with self.subTest('attach to chain'):
                data = self.post_new(
                    data={
                        'name': 'Chain Abyss',
                        'parent': self.chain_bottom.pk,
                        'goal': 50,
                    },
                )
                serialized = self._serialize_models(
                    models.Bid.objects.get(pk=data['id'])
                )
                self.assertEqual(data, serialized)

            with self.suppressSnapshot(), self.subTest('create hidden states'):
                for state in models.Bid.HIDDEN_STATES:
                    with self.subTest(state):
                        data = {'name': state.capitalize(), 'state': state}
                        if state == 'HIDDEN':
                            data['event'] = self.event.pk
                            data['goal'] = 50
                        else:
                            data['parent'] = self.opened_parent_bid.pk
                            data['istarget'] = True
                        data = self.post_new(data=data)
                        serialized = self._serialize_models(
                            models.Bid.objects.get(pk=data['id']),
                            include_hidden=True,
                            with_permissions=('tracker.view_bid'),
                        )
                        self.assertEqual(data, serialized)

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

            with self.subTest('event is archived'):
                self.post_new(
                    data={
                        'name': 'New Archived Event Bid 2',
                        'event': self.archived_event.pk,
                    },
                    user=self.add_user,
                    status_code=403,
                )

                self.post_new(
                    data={
                        'name': 'New Archived Run Bid 2',
                        'speedrun': self.archived_run.pk,
                    },
                    status_code=403,
                )

                self.post_new(
                    data={
                        'name': 'New Archived Child 2',
                        'parent': self.archived_parent_bid.pk,
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

        with self.assertLogsChanges(3), self.subTest('changing to hidden states'):
            data = self.patch_detail(self.challenge, data={'state': 'HIDDEN'})
            self.assertV2ModelPresent(
                self.challenge,
                data,
                serializer_kwargs=(
                    dict(include_hidden=True, with_permissions=('tracker.view_bid'))
                ),
            )
            data = self.patch_detail(self.opened_bid, data={'state': 'DENIED'})
            self.assertV2ModelPresent(
                self.opened_bid,
                data,
                serializer_kwargs=(
                    dict(include_hidden=True, with_permissions=('tracker.view_bid'))
                ),
            )
            data = self.patch_detail(self.opened_bid, data={'state': 'PENDING'})
            self.assertV2ModelPresent(
                self.opened_bid,
                data,
                serializer_kwargs=(
                    dict(include_hidden=True, with_permissions=('tracker.view_bid'))
                ),
            )

        with self.assertLogsChanges(2), self.subTest('bid approval'):
            self.pending_bid.state = 'PENDING'
            self.pending_bid.save()
            data = self.patch_noun(self.pending_bid, 'approve')
            self.assertV2ModelPresent(
                self.pending_bid,
                data,
            )
            self.pending_bid.state = 'PENDING'
            self.pending_bid.save()
            data = self.patch_noun(self.pending_bid, 'deny')
            self.assertV2ModelPresent(
                self.pending_bid,
                data,
                serializer_kwargs=(
                    dict(include_hidden=True, with_permissions=('tracker.view_bid'))
                ),
            )

        with self.subTest('approval only user'), self.assertLogsChanges(2):
            self.pending_bid.state = 'PENDING'
            self.pending_bid.save()
            self.patch_noun(self.pending_bid, 'approve', user=self.approval_user)
            self.pending_bid.state = 'PENDING'
            self.pending_bid.save()
            self.patch_noun(self.pending_bid, 'deny', user=self.approval_user)

        with (
            self.subTest('can edit top level bids even without creation permission'),
            self.assertLogsChanges(1),
        ):
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

        with self.subTest(
            'approve deny on an archived event non-option should still 404'
        ):
            self.patch_noun(self.archived_challenge, 'approve', status_code=404)
            self.patch_noun(self.archived_challenge, 'deny', status_code=404)

        with self.subTest('should not be able to edit an archived bid'):
            self.patch_detail(
                self.archived_challenge,
                data={'name': 'Archived Updated Again'},
                status_code=403,
            )
            self.patch_noun(self.archived_pending_bid, 'approve', status_code=403)
            self.patch_noun(self.archived_pending_bid, 'deny', status_code=403)

        with self.subTest('should not be able to move to an archived event'):
            self.patch_detail(
                self.opened_parent_bid,
                data={'event': self.archived_event.pk},
                status_code=403,
            )
            self.patch_detail(
                self.opened_parent_bid,
                data={'speedrun': self.archived_run.pk},
                status_code=403,
            )

        with self.subTest('approve and deny without user options'):
            self.patch_noun(self.closed_parent_bid, 'approve', status_code=404)
            self.patch_noun(self.closed_parent_bid, 'deny', status_code=404)
            self.patch_noun(self.closed_bid, 'approve', status_code=404)
            self.patch_noun(self.closed_bid, 'deny', status_code=404)

        with self.subTest('anonymous'):
            self.patch_detail(
                self.opened_parent_bid,
                data={'name': 'Opened Parent Updated Anonymous'},
                status_code=403,
                user=None,
            )
            self.patch_noun(self.opened_bid, 'approve', status_code=403, user=None)
            self.patch_noun(self.opened_bid, 'deny', status_code=403, user=None)


class TestBidSerializer(TestBidBase, APITestCase):
    serializer_class = BidSerializer

    def _format_bid(self, bid, *, with_event=True, child=False, tree=None):
        if tree is None:
            tree = child

        def full_name(bid):
            parts = []
            if bid.parent:
                parts.append(full_name(bid.parent))
            elif bid.speedrun:
                parts.append(bid.speedrun.name)
                if bid.speedrun.category:
                    parts.append(bid.speedrun.category)
            parts.append(bid.name)
            return ' -- '.join(parts)

        data = {
            'type': 'bid',
            'id': bid.id,
            'name': bid.name,
            'full_name': full_name(bid),
            'state': bid.state,
            'description': bid.description,
            'shortdescription': bid.shortdescription,
            'estimate': bid.estimate,
            'total': bid.total,
            'count': bid.count,
            'istarget': bid.istarget,
            'revealedtime': bid.revealedtime,
            'close_at': bid.close_at,
            'post_run': bid.post_run,
        }
        if not child:
            data = {
                **data,
                'speedrun': bid.speedrun_id,
                'goal': bid.goal,
                'chain': bid.chain,
            }
            if with_event:
                data['event'] = bid.event_id
            if not (bid.chain or bid.parent):  # neither child nor chain
                data = {
                    **data,
                    'repeat': bid.repeat,
                }
                if not bid.istarget:
                    data = {
                        **data,
                        'accepted_number': bid.accepted_number,
                        'allowuseroptions': bid.allowuseroptions,
                    }
        elif not bid.chain:
            del data['post_run']
            del data['close_at']
        if not tree:
            data['level'] = bid.level
            data['parent'] = bid.parent_id
        if bid.parent_id and not bid.chain:
            data['bid_type'] = 'option' if bid.istarget else 'choice'
        elif bid.istarget:
            data['bid_type'] = 'challenge'
        if bid.allowuseroptions:
            data = {**data, 'option_max_length': bid.option_max_length}
        if bid.chain:
            data = {
                **data,
                'bid_type': 'challenge',
                'goal': bid.goal,
                'chain_goal': bid.chain_goal,
                'chain_remaining': bid.chain_remaining,
            }
            if bid.istarget and tree:
                data['chain_steps'] = [
                    self._format_bid(chain, child=True)
                    for chain in bid.get_descendants()
                ]
        elif not bid.istarget and tree:
            data['options'] = [
                self._format_bid(option, child=True) for option in bid.get_children()
            ]

        return data

    def test_single(self):
        with self.subTest('chained bid'):
            # TODO
            # serialized = self._serialize_models(self.chain_top)
            # self.assertV2ModelPresent(self._format_bid(self.chain_top, tree=False), serialized)

            serialized = self._serialize_models(self.chain_top, tree=True)
            self.assertV2ModelPresent(
                self._format_bid(self.chain_top, tree=True), serialized
            )
            self.assertV2ModelPresent(
                self._format_bid(self.chain_middle, child=True),
                serialized['chain_steps'],
                partial=True,
            )
            self.assertV2ModelPresent(
                self._format_bid(self.chain_bottom, child=True),
                serialized['chain_steps'],
                partial=True,
            )
            serialized = self._serialize_models(self.chain_middle)
            self.assertV2ModelPresent(self._format_bid(self.chain_middle), serialized)
            serialized = self._serialize_models(self.chain_bottom)
            self.assertV2ModelPresent(self._format_bid(self.chain_bottom), serialized)

        with self.subTest('bid with options'):
            serialized = self._serialize_models(self.opened_parent_bid, tree=True)

            formatted = self._format_bid(self.opened_parent_bid, tree=True)
            del formatted['options']  # checking the options individually
            self.assertV2ModelPresent(
                formatted,
                serialized,
                partial=True,
            )

            with self.subTest('should include the public children'):
                self.assertV2ModelPresent(
                    self._format_bid(self.opened_bid, child=True),
                    serialized['options'],
                )

            with self.subTest(
                'should not include the hidden children unless specifically asked and the permission is included'
            ):
                self.assertV2ModelNotPresent(
                    self._format_bid(self.denied_bid, child=True),
                    serialized['options'],
                )
                self.assertV2ModelNotPresent(
                    self._format_bid(self.pending_bid, child=True),
                    serialized['options'],
                )

            with self.subTest(
                'should include hidden children when requested and given the correct permission'
            ):
                serialized = self._serialize_models(
                    self.opened_parent_bid,
                    tree=True,
                    include_hidden=True,
                    with_permissions=('tracker.view_bid',),
                )
                self.assertV2ModelPresent(
                    self._format_bid(self.denied_bid, child=True),
                    serialized['options'],
                )
                self.assertV2ModelPresent(
                    self._format_bid(self.pending_bid, child=True),
                    serialized['options'],
                )

        with self.subTest('hidden permissions checks'):
            for bid in [
                self.pending_bid,
                self.denied_bid,
                self.hidden_bid,
                self.hidden_parent_bid,
            ]:
                bid.refresh_from_db()  # ensure tree is up to date
                # smoke test for base case
                with self.assertRaises(AssertionError):
                    BidSerializer(bid).to_representation(bid)

                # flag isn't enough, permission needs to be provided
                with self.assertRaises(AssertionError):
                    BidSerializer(bid, include_hidden=True).to_representation(bid)

                # permission isn't enough, the flag needs to be specified too
                with self.assertRaises(AssertionError):
                    BidSerializer(
                        bid, with_permissions='tracker.view_bid'
                    ).to_representation(bid)

                # any of the following permissions are sufficient
                for perm in [
                    'tracker.view_bid',
                    'tracker.change_bid',
                ]:
                    BidSerializer(
                        bid, include_hidden=True, with_permissions=perm
                    ).to_representation(bid)

        with self.subTest('child bid'):
            serialized = self._serialize_models(self.opened_bid)
            self.assertV2ModelPresent(self._format_bid(self.opened_bid), serialized)

        with self.subTest('branch bid'):
            self.opened_bid.istarget = False
            self.opened_bid.save()

            serialized = self._serialize_models(self.opened_bid)
            self.assertV2ModelPresent(self._format_bid(self.opened_bid), serialized)
