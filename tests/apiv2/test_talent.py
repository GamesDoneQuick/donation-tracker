from django.db.models import Q

from tests import randgen
from tests.util import APITestCase
from tracker import models
from tracker.api.serializers import TalentSerializer


class TestTalent(APITestCase):
    model_name = 'talent'
    serializer_class = TalentSerializer

    def setUp(self):
        super().setUp()
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
        self.interviewer = randgen.generate_interviewer(self.rand)
        self.interviewer.save()
        self.subject = randgen.generate_subject(self.rand)
        self.subject.save()
        self.other_talent = randgen.generate_talent(
            self.rand, 'not attached to anything'
        )
        self.other_talent.save()
        self.spread_talent = randgen.generate_talent(self.rand)
        self.spread_talent.save()
        self.spread_draft_talent = randgen.generate_talent(self.rand)
        self.spread_draft_talent.save()
        self.runs = randgen.generate_runs(
            self.rand, num_runs=2, event=self.event, ordered=True
        )
        self.runner.runs.add(*self.runs)
        self.host.hosting.add(*self.runs)
        self.commentator.commentating.add(*self.runs)
        self.interview = randgen.generate_interview(self.rand, event=self.event)
        self.interview.save()
        self.interview.interviewers.add(self.interviewer)
        self.interview.subjects.add(self.subject)
        self.spread_runs = randgen.generate_runs(
            self.rand, num_runs=3, event=self.event, ordered=True
        )
        self.spread_draft_runs = randgen.generate_runs(
            self.rand, num_runs=3, event=self.draft_event, ordered=True
        )
        self.spread_interviews = []
        self.spread_draft_interviews = []
        for _ in range(2):
            i = randgen.generate_interview(self.rand, event=self.event)
            i.save()
            self.spread_interviews.append(i)
            i = randgen.generate_interview(self.rand, event=self.draft_event)
            i.save()
            self.spread_draft_interviews.append(i)
        self.spread_talent.runs.add(self.spread_runs[0])
        self.spread_talent.hosting.add(self.spread_runs[1])
        self.spread_talent.commentating.add(self.spread_runs[2])
        self.spread_talent.interviewer_for.add(self.spread_interviews[0])
        self.spread_talent.subject_for.add(self.spread_interviews[1])
        self.spread_draft_talent.runs.add(self.spread_draft_runs[0])
        self.spread_draft_talent.hosting.add(self.spread_draft_runs[1])
        self.spread_draft_talent.commentating.add(self.spread_draft_runs[2])
        self.spread_draft_talent.interviewer_for.add(self.spread_draft_interviews[0])
        self.spread_draft_talent.subject_for.add(self.spread_draft_interviews[1])
        self.other_runs = randgen.generate_runs(
            self.rand, num_runs=1, event=self.other_event, ordered=True
        )
        self.other_runner.runs.add(*self.other_runs)

    def test_fetch(self):
        self.client.force_login(self.view_user)
        with self.saveSnapshot():
            with self.subTest('generic lists'):
                # participants of any kind

                data = self.get_list()
                self.assertExactV2Models(
                    {
                        self.runner,
                        self.other_runner,
                        self.host,
                        self.commentator,
                        self.interviewer,
                        self.subject,
                        self.other_talent,
                        self.spread_talent,
                        self.spread_draft_talent,
                    },
                    data,
                )

                data = self.get_list(kwargs={'event_pk': self.event.pk})
                self.assertExactV2Models(
                    {
                        self.runner,
                        self.host,
                        self.commentator,
                        self.interviewer,
                        self.subject,
                        self.spread_talent,
                    },
                    data,
                )

                data = self.get_list(kwargs={'event_pk': self.draft_event.pk})
                self.assertExactV2Models([self.spread_draft_talent], data)

            with self.subTest('search'):
                data = self.get_list(data={'name': self.runner.name})
                self.assertExactV2Models([self.runner], data)

            with self.subTest('filtered lists'):
                data = self.get_noun('runners')
                self.assertExactV2Models(
                    {self.runner, self.other_runner, self.spread_talent}, data
                )

                data = self.get_noun('runners', kwargs={'event_pk': self.event.pk})
                self.assertExactV2Models({self.runner, self.spread_talent}, data)

                data = self.get_noun(
                    'runners', kwargs={'event_pk': self.other_event.pk}
                )
                self.assertExactV2Models({self.other_runner}, data)

                data = self.get_noun(
                    'runners', kwargs={'event_pk': self.draft_event.pk}
                )
                self.assertExactV2Models({self.spread_draft_talent}, data)

                data = self.get_noun('hosts')
                self.assertExactV2Models({self.host, self.spread_talent}, data)

                data = self.get_noun('hosts', kwargs={'event_pk': self.other_event.pk})
                self.assertEmptyModels(data)

                data = self.get_noun('hosts', kwargs={'event_pk': self.draft_event.pk})
                self.assertExactV2Models({self.spread_draft_talent}, data)

                data = self.get_noun('commentators')
                self.assertExactV2Models({self.commentator, self.spread_talent}, data)

                data = self.get_noun(
                    'commentators', kwargs={'event_pk': self.other_event.pk}
                )
                self.assertEmptyModels(data)

                data = self.get_noun(
                    'commentators', kwargs={'event_pk': self.draft_event.pk}
                )
                self.assertExactV2Models({self.spread_draft_talent}, data)

                data = self.get_noun('interviewers')
                self.assertExactV2Models({self.interviewer, self.spread_talent}, data)

                data = self.get_noun(
                    'interviewers', kwargs={'event_pk': self.other_event.pk}
                )
                self.assertEmptyModels(data)

                data = self.get_noun(
                    'interviewers', kwargs={'event_pk': self.draft_event.pk}
                )
                self.assertExactV2Models({self.spread_draft_talent}, data)

                data = self.get_noun('subjects')
                self.assertExactV2Models({self.subject, self.spread_talent}, data)

                data = self.get_noun(
                    'subjects', kwargs={'event_pk': self.other_event.pk}
                )
                self.assertEmptyModels(data)

                data = self.get_noun(
                    'subjects', kwargs={'event_pk': self.draft_event.pk}
                )
                self.assertExactV2Models({self.spread_draft_talent}, data)

            with self.subTest('reverse lists'):
                for noun in [
                    'participating',
                    'interviews',
                    'runs',
                    'hosting',
                    'commentating',
                    'interviewer',
                    'subject',
                ]:
                    for model in models.Talent.objects.all():
                        for event in [None, *models.Event.objects.all()]:
                            if event:
                                q = Q(event=event)
                                kwargs = {'event_pk': event.pk}
                            else:
                                q = Q(event__draft=False)
                                kwargs = {}

                            if noun == 'participating':
                                expected = {
                                    *model.runs.filter(q),
                                    *model.hosting.filter(q),
                                    *model.commentating.filter(q),
                                }
                            elif noun == 'runs':
                                expected = {*model.runs.filter(q)}
                            elif noun == 'hosting':
                                expected = {*model.hosting.filter(q)}
                            elif noun == 'commentating':
                                expected = {*model.commentating.filter(q)}
                            elif noun == 'interviews':
                                expected = {
                                    *model.interviewer_for.filter(q),
                                    *model.subject_for.filter(q),
                                }
                            elif noun == 'interviewer':
                                expected = {*model.interviewer_for.filter(q)}
                            elif noun == 'subject':
                                expected = {*model.subject_for.filter(q)}
                            else:
                                self.fail(f'unhandled noun {noun}')

                            # possible FIXME, see viewset code
                            if event:
                                exists_in_event = models.Talent.objects.filter(
                                    Q(runs__event=event)
                                    | Q(hosting__event=event)
                                    | Q(commentating__event=event)
                                    | Q(interviewer_for__event=event)
                                    | Q(subject_for__event=event),
                                    id=model.id,
                                ).exists()
                            else:
                                exists_in_event = True

                            if exists_in_event:
                                if expected:
                                    data = self.get_noun(noun, model, kwargs=kwargs)[
                                        'results'
                                    ]
                                else:
                                    with self.suppressSnapshot():
                                        data = self.get_noun(
                                            noun, model, kwargs=kwargs
                                        )['results']

                                self.assertSetEqual(
                                    {d['id'] for d in data}, {e.id for e in expected}
                                )
                            else:
                                # see possible FIXME in the viewset code, should this return a 404 or an empty list?
                                with self.suppressSnapshot():
                                    self.get_noun(
                                        noun, model, kwargs=kwargs, status_code=404
                                    )

        with self.subTest('error cases'):
            self.client.force_authenticate(None)

            self.get_list(kwargs={'event_pk': self.draft_event.pk}, status_code=404)

            for noun in [
                'runners',
                'hosts',
                'commentators',
                'interviewers',
                'subjects',
            ]:
                self.get_noun(
                    noun, kwargs={'event_pk': self.draft_event.pk}, status_code=404
                )

            self.get_detail(
                self.runner, kwargs={'event_pk': self.draft_event.pk}, status_code=404
            )

            for noun in [
                'participating',
                'interviews',
                'runs',
                'hosting',
                'commentating',
                'interviewer',
                'subject',
            ]:
                self.get_noun(
                    noun,
                    self.runner,
                    kwargs={'event_pk': self.draft_event.pk},
                    status_code=404,
                )

    def test_create(self):
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
            self.post_new(
                data={'name': 'spikevegeta'},
                status_code=400,
                expected_error_codes='unique',
            )

        with self.subTest('permissions check'):
            self.post_new(user=self.view_user, status_code=403)
            self.post_new(user=None, status_code=403)

    def test_patch(self):
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

        with self.subTest('already exists'):
            self.patch_detail(
                self.other_runner,
                data={'name': 'spikevegeta'},
                status_code=400,
                expected_error_codes='unique',
            )

        with self.subTest('permissions check'):
            self.patch_detail(self.runner, user=self.view_user, status_code=403)
            self.patch_detail(self.runner, user=None, status_code=403)
