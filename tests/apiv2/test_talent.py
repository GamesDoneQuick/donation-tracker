import random

from tests import randgen
from tests.util import APITestCase
from tracker import models
from tracker.api.serializers import TalentSerializer


class TestTalent(APITestCase):
    model_name = 'talent'
    serializer_class = TalentSerializer

    def setUp(self):
        super().setUp()
        self.rand = random.Random()
        self.event = randgen.generate_event(self.rand)
        self.event.save()
        self.other_event = randgen.generate_event(self.rand)
        self.other_event.save()
        self.runner = randgen.generate_runner(self.rand)
        self.runner.save()
        self.other_runner = randgen.generate_runner(self.rand)
        self.other_runner.save()
        self.host = randgen.generate_host(self.rand)
        self.host.save()
        self.commentator = randgen.generate_commentator(self.rand)
        self.commentator.save()
        self.other_talent = randgen.generate_talent(self.rand)
        self.other_talent.save()
        self.runs = randgen.generate_runs(
            self.rand, num_runs=2, event=self.event, ordered=True
        )
        self.runner.runs.add(*self.runs)
        self.host.hosting.add(*self.runs)
        self.commentator.commentating.add(*self.runs)
        self.other_runs = randgen.generate_runs(
            self.rand, num_runs=1, event=self.other_event, ordered=True
        )
        self.other_runner.runs.add(*self.other_runs)

    def test_talent_fetch(self):
        with self.saveSnapshot():
            with self.subTest('generic lists'):
                # participants of any kind

                data = self.get_list()['results']
                self.assertEqual(len(data), 5)
                self.assertV2ModelPresent(self.runner, data)
                self.assertV2ModelPresent(self.other_runner, data)
                self.assertV2ModelPresent(self.host, data)
                self.assertV2ModelPresent(self.commentator, data)
                self.assertV2ModelPresent(self.other_talent, data)

                data = self.get_list(kwargs={'event_pk': self.event.pk})['results']
                self.assertEqual(len(data), 3)
                self.assertV2ModelPresent(self.runner, data)
                self.assertV2ModelPresent(self.host, data)
                self.assertV2ModelPresent(self.commentator, data)

            with self.subTest('filtered lists'):
                data = self.get_noun('runners')['results']
                self.assertEqual(len(data), 2)
                self.assertV2ModelPresent(self.runner, data)
                self.assertV2ModelPresent(self.other_runner, data)

                data = self.get_noun('runners', kwargs={'event_pk': self.event.pk})[
                    'results'
                ]
                self.assertEqual(len(data), 1)
                self.assertV2ModelPresent(self.runner, data)

                data = self.get_noun(
                    'runners', kwargs={'event_pk': self.other_event.pk}
                )['results']
                self.assertEqual(len(data), 1)
                self.assertV2ModelPresent(self.other_runner, data)

                data = self.get_noun('hosts')['results']
                self.assertEqual(len(data), 1)
                self.assertV2ModelPresent(self.host, data)

                data = self.get_noun('hosts', kwargs={'event_pk': self.other_event.pk})[
                    'results'
                ]
                self.assertEqual(len(data), 0)

                data = self.get_noun('commentators')['results']
                self.assertEqual(len(data), 1)
                self.assertV2ModelPresent(self.commentator, data)

                data = self.get_noun(
                    'commentators', kwargs={'event_pk': self.other_event.pk}
                )['results']
                self.assertEqual(len(data), 0)

            # TODO: verify the right runs? not sure if it's worth the exhaustiveness

            with self.subTest('reverse lists'):
                data = self.get_noun('participating', self.runner)['results']
                self.assertEqual(len(data), 2)

                # see possible FIXME in the viewset code, should this return a 404 or an empty list?
                self.get_noun(
                    'participating',
                    self.runner,
                    kwargs={'event_pk': self.other_event.pk},
                    status_code=404,
                )

                data = self.get_noun('participating', self.other_runner)['results']
                self.assertEqual(len(data), 1)

                data = self.get_noun('participating', self.host)['results']
                self.assertEqual(len(data), 2)

                data = self.get_noun('participating', self.commentator)['results']
                self.assertEqual(len(data), 2)

                data = self.get_noun('participating', self.other_talent)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('runs', self.runner)['results']
                self.assertEqual(len(data), 2)

                data = self.get_noun('runs', self.other_runner)['results']
                self.assertEqual(len(data), 1)

                data = self.get_noun('runs', self.host)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('runs', self.commentator)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('runs', self.other_talent)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('hosting', self.runner)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('hosting', self.other_runner)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('hosting', self.host)['results']
                self.assertEqual(len(data), 2)

                data = self.get_noun('hosting', self.commentator)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('hosting', self.other_talent)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('commentating', self.runner)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('commentating', self.other_runner)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('commentating', self.host)['results']
                self.assertEqual(len(data), 0)

                data = self.get_noun('commentating', self.commentator)['results']
                self.assertEqual(len(data), 2)

                data = self.get_noun('commentating', self.other_talent)['results']
                self.assertEqual(len(data), 0)

    def test_talent_create(self):
        self.client.force_login(self.add_user)

        with self.saveSnapshot():
            with self.subTest('minimal'):
                data = self.post_new(data={'name': 'puwexil'})
                talent = models.Talent.objects.get(pk=data['id'])
                self.assertEqual(talent.name, 'puwexil')

            with self.subTest('full-blown'):
                data = self.post_new(
                    data={
                        'name': 'SpikeVegeta',
                        'stream': 'http://deadbeef.com/',
                        'twitter': 'SpikeVegeta',
                        'youtube': 'SpikeVegeta',
                        'pronouns': 'he/him',
                    }
                )
                talent = models.Talent.objects.get(pk=data['id'])
                self.assertEqual(talent.name, 'SpikeVegeta')
                self.assertEqual(talent.stream, 'http://deadbeef.com/')
                self.assertEqual(talent.twitter, 'SpikeVegeta')
                self.assertEqual(talent.youtube, 'SpikeVegeta')
                self.assertEqual(talent.pronouns, 'he/him')

        with self.subTest('already exists'):
            self.post_new(data={'name': 'spikevegeta'}, status_code=400)

        with self.subTest('permissions check'):
            self.post_new(user=self.view_user, status_code=403)
            self.post_new(user=None, status_code=403)

    def test_talent_update(self):
        self.client.force_login(self.add_user)

        with self.saveSnapshot():
            with self.subTest('full-blown'):
                self.patch_detail(
                    self.runner,
                    data={
                        'name': 'SpikeVegeta',
                        'stream': 'http://deadbeef.com/',
                        'twitter': 'SpikeVegeta',
                        'youtube': 'SpikeVegeta',
                        'pronouns': 'he/him',
                    },
                )
                self.runner.refresh_from_db()
                self.assertEqual(self.runner.name, 'SpikeVegeta')
                self.assertEqual(self.runner.stream, 'http://deadbeef.com/')
                self.assertEqual(self.runner.twitter, 'SpikeVegeta')
                self.assertEqual(self.runner.youtube, 'SpikeVegeta')
                self.assertEqual(self.runner.pronouns, 'he/him')

        with self.subTest('validation'):
            self.patch_detail(
                self.other_runner, data={'name': 'spikevegeta'}, status_code=400
            )

        with self.subTest('permissions check'):
            self.patch_detail(self.runner, user=self.view_user, status_code=403)
            self.patch_detail(self.runner, user=None, status_code=403)
