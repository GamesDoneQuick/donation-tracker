from typing import List

from django.contrib.auth.models import Group, Permission, User
from rest_framework.test import APIClient

from ..util import APITestCase


def me_response(*, username: str, staff: bool, superuser: bool, permissions: List[str]):
    return {
        'username': username,
        'staff': staff,
        'superuser': superuser,
        'permissions': permissions,
    }


class TestMe(APITestCase):
    def setUp(self):
        super(TestMe, self).setUp()
        self.client = APIClient()

    def test_normal_user(self):
        normal_user = User.objects.create(username='normal user')
        self.client.force_authenticate(user=normal_user)
        response = self.client.get('/tracker/api/v2/me/')

        self.assertDictEqual(
            response.data,
            me_response(
                username=normal_user.username,
                staff=False,
                superuser=False,
                permissions=[],
            ),
        )

    def test_staff_user(self):
        staff = User.objects.create(username='staff user', is_staff=True)
        self.client.force_authenticate(user=staff)
        response = self.client.get('/tracker/api/v2/me/')
        self.assertDictEqual(
            response.data,
            me_response(
                username=staff.username,
                staff=True,
                superuser=False,
                permissions=[],
            ),
        )

    def test_super_user(self):
        super_user = User.objects.create(username='super user', is_superuser=True)
        self.client.force_authenticate(user=super_user)
        response = self.client.get('/tracker/api/v2/me/')
        self.assertDictContainsSubset(
            {'username': super_user.username, 'staff': False, 'superuser': True},
            response.data,
        )
        self.assertSetEqual(
            set(response.data['permissions']), super_user.get_all_permissions()
        )

    def test_user_with_permissions(self):
        user = User.objects.create(username='user with permissions')
        user.user_permissions.add(Permission.objects.get(codename='add_user'))

        self.client.force_authenticate(user=user)
        response = self.client.get('/tracker/api/v2/me/')
        self.assertDictEqual(
            response.data,
            me_response(
                username=user.username,
                staff=False,
                superuser=False,
                permissions=['auth.add_user'],
            ),
        )

    def test_user_with_group_permissions(self):
        normal_user = User.objects.create(username='normal user')

        group = Group.objects.create(name='Test Group')
        group.permissions.add(Permission.objects.get(codename='add_user'))
        group.user_set.add(normal_user)

        self.client.force_authenticate(user=normal_user)
        response = self.client.get('/tracker/api/v2/me/')
        self.assertDictEqual(
            response.data,
            me_response(
                username=normal_user.username,
                staff=False,
                superuser=False,
                permissions=['auth.add_user'],
            ),
        )

    def test_anonymous_user(self):
        response = self.client.get('/tracker/api/v2/me/')
        self.assertEqual(response.status_code, 403)
