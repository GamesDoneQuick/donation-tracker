from tests.util import APITestCase
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
        self.post_new(
            model_name='interview',
            data={'anchor': {'no': 'nesting'}},
            user=self.super_user,
            status_code=400,
            expected_error_codes={'anchor': messages.NO_NESTED_CREATES_CODE},
        )

        self.post_new(
            model_name='speedrun',
            data={'runners': [{'also': 'nesting'}]},
            status_code=400,
            expected_error_codes={'runners': messages.NO_NESTED_CREATES_CODE},
        )
