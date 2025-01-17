from django.urls import reverse

from tests.util import APITestCase
from tracker import models
from tracker.api import messages


class TestAPI(APITestCase):
    # not really generic but these need to be tested somewhere

    def test_coalesce_errors(self):
        self.post_new(
            model_name='bid',
            data={
                'event': 'foo',
                'parent': 'bar',
            },
            user=self.super_user,
            status_code=400,
            expected_error_codes={
                'event': 'incorrect_type',
                'parent': 'incorrect_type',
            },
        )

    def test_bad_nesting(self):
        # TODO: re-add a case where this would be true
        # self.post_new(
        #     model_name='interview',
        #     data={'anchor': {'no': 'nesting'}},
        #     user=self.super_user,
        #     status_code=400,
        #     expected_error_codes={'anchor': messages.NO_NESTED_CREATES_CODE},
        # )

        self.post_new(
            model_name='speedrun',
            data={'runners': [{'also': 'nesting'}]},
            user=self.super_user,
            status_code=400,
            expected_error_codes={'runners': messages.NO_NESTED_CREATES_CODE},
        )

    def test_validate(self):
        models.Talent.objects.create(name='Bar')
        with self.subTest('creates'), self.assertLogsChanges(0):
            self.post_noun(
                'validate',
                model_name='interview',
                status_code=202,
                view_name='validate-create',
                data={
                    'event': self.event.pk,
                    'order': 1,
                    'suborder': 1,
                    'topic': 'Foo',
                    'interviewers': ['Bar'],
                    'length': '5:00',
                },
                user=self.super_user,
            )
            data = self.post_noun(
                'validate',
                model_name='interview',
                status_code=400,
                view_name='validate-create',
                data=[
                    {
                        'event': self.event.pk,
                        'order': 1,
                        'suborder': 1,
                        'topic': 'Foo',
                        'interviewers': ['Bar'],
                        'length': '5:00',
                    },
                    {},
                ],
            )
            self.assertIsNone(data['valid'][1])
            self.assertIsNone(data['invalid'][0])
            self.assertIsInstance(data['valid'][0], dict)
            self.assertIsInstance(data['invalid'][1], dict)

        with self.subTest('updates'), self.assertLogsChanges(0):
            interview = models.Interview.objects.create(
                event=self.event, order=1, suborder=1, topic='Bar'
            )
            self.patch_noun(
                interview,
                'validate',
                model_name='interview',
                view_name='validate-update',
                data={'topic': 'Changed Topic'},
                status_code=202,
            )
            self.patch_noun(
                interview,
                'validate',
                model_name='interview',
                view_name='validate-update',
                data={},
                status_code=202,
            )

            self.patch_noun(
                interview,
                'validate',
                model_name='interview',
                view_name='validate-update',
                data={'interviewers': ['Nonsense']},
                status_code=400,
                expected_error_codes={
                    'interviewers': messages.INVALID_NATURAL_KEY_CODE
                },
            )

            self.patch_noun(
                interview,
                'validate',
                model_name='interview',
                view_name='validate-update',
                data={'topic': ''},
                status_code=400,
                expected_error_codes={'topic': 'blank'},
            )

            resp = self.client.patch(
                reverse('tracker:api_v2:interview-validate-update', args=(123456,)),
                data={},
                format='json',
            )
            self.assertEqual(resp.status_code, 404)
