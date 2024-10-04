from django.core.exceptions import ValidationError
from django.test import TransactionTestCase

import tracker.models as models
from tests.util import MigrationsTestCase, today_noon


class TestTalent(TransactionTestCase):
    def test_name_case_insensitivity(self):
        runner = models.Talent.objects.create(name='lowercase')
        runner.full_clean()  # does not trigger itself
        with self.assertRaises(ValidationError):
            models.Talent(name='LOWERCASE').full_clean()


class TestRunnerHeadsetMigration(MigrationsTestCase):
    migrate_from = [('tracker', '0043_add_model_tags')]
    migrate_to = [('tracker', '0047_merge_talent_contenttypes')]

    def setUpBeforeMigration(self, apps):
        # testing the permissions rename is super annoying, because of the timing around CT/Permission creation
        #  consider writing a helper if we do this again
        User = apps.get_model('auth', 'User')
        Group = apps.get_model('auth', 'Group')
        Permission = apps.get_model('auth', 'Permission')
        ContentType = apps.get_model('contenttypes', 'ContentType')
        for n in ['runner', 'headset']:
            ct = ContentType.objects.get_or_create(app_label='tracker', model=n)[0]
            for c in ['add', 'change', 'delete', 'view']:
                Permission.objects.get_or_create(
                    content_type=ct, codename=f'{c}_{n}', name=f'Can {c} {n}'
                )
        ContentType.objects.filter(app_label='tracker', model='talent').delete()
        user = User.objects.create(username='runner_editor')
        user.user_permissions.add(
            *Permission.objects.filter(
                content_type__app_label='tracker', content_type__model='runner'
            )
        )
        group = Group.objects.create(name='Headset Editor')
        group.permissions.add(
            *Permission.objects.filter(
                content_type__app_label='tracker', content_type__model='headset'
            )
        )
        Event = apps.get_model('tracker', 'Event')
        SpeedRun = apps.get_model('tracker', 'SpeedRun')
        event = Event.objects.create(
            name='Test Event', short='test', datetime=today_noon
        )
        run = SpeedRun.objects.create(name='Test Run', event=event)
        Runner = apps.get_model('tracker', 'Runner')
        Headset = apps.get_model('tracker', 'Headset')
        Runner.objects.create(name='SpikeVegeta')
        runner = Runner.objects.create(name='puwexil')
        Runner.objects.create(name='Charbunny')
        headset1 = Headset.objects.create(name='SpikeVegeta')
        Headset.objects.create(
            name='hmm', runner=runner
        )  # runner name wins if attached and disagrees
        headset2 = Headset.objects.create(
            name='CharBunny', pronouns='she/her'
        )  # check case insensitivity, runner wins
        run.runners.add(runner)
        run.hosts.add(headset2)
        run.commentators.add(headset1)

    def test_after_migration(self):
        Talent = self.apps.get_model('tracker', 'Talent')
        SpeedRun = self.apps.get_model('tracker', 'SpeedRun')
        User = self.apps.get_model('auth', 'User')
        Group = self.apps.get_model('auth', 'Group')
        self.assertEqual(Talent.objects.count(), 3, 'Talent count incorrect')
        self.assertSetEqual(
            {'SpikeVegeta', 'puwexil', 'Charbunny'},
            {p.name for p in Talent.objects.all()},
            'Wrong set of names',
        )
        self.assertEqual(Talent.objects.get(name='Charbunny').pronouns, 'she/her')
        run = SpeedRun.objects.get(name='Test Run', event__short='test')
        self.assertSequenceEqual(['puwexil'], [r.name for r in run.runners.all()])
        self.assertSequenceEqual(
            ['SpikeVegeta'], [c.name for c in run.commentators.all()]
        )
        self.assertSequenceEqual(['Charbunny'], [h.name for h in run.hosts.all()])
        user = User.objects.prefetch_related('user_permissions').get(
            username='runner_editor'
        )
        group = Group.objects.prefetch_related('permissions').get(name='Headset Editor')
        for c in ['add', 'change', 'delete', 'view']:
            self.assertIsNotNone(
                next(
                    (
                        p
                        for p in user.user_permissions.all()
                        if p.codename == f'{c}_talent'
                    ),
                    None,
                ),
                msg='User permission did not migrate',
            )
            self.assertIsNotNone(
                next(
                    (p for p in group.permissions.all() if p.codename == f'{c}_talent'),
                    None,
                ),
                msg='Group permission did not migrate',
            )


class TestReversedRunnerHeadsetMigration(MigrationsTestCase):
    migrate_from = [('tracker', '0046_rename_runner_and_headset')]
    migrate_to = [('tracker', '0043_add_model_tags')]

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        Run = apps.get_model('tracker', 'SpeedRun')
        event = Event.objects.create(
            name='Test Event', short='test', datetime=today_noon
        )
        run = Run.objects.create(name='Test Run', event=event)
        Talent = apps.get_model('tracker', 'Talent')
        runner = Talent.objects.create(name='puwexil')
        host = Talent.objects.create(name='Charbunny')
        commentator = Talent.objects.create(name='SpikeVegeta')
        run.runners.add(runner)
        run.hosts.add(host)
        run.commentators.add(commentator)

    def test_reversed_after_migration(self):
        Runner = self.apps.get_model('tracker', 'Runner')
        Headset = self.apps.get_model('tracker', 'Headset')
        SpeedRun = self.apps.get_model('tracker', 'SpeedRun')
        self.assertSetEqual(
            {'SpikeVegeta', 'puwexil', 'Charbunny'},
            {p.name for p in Runner.objects.all()},
            'Wrong set of names',
        )
        self.assertSetEqual(
            {'SpikeVegeta', 'Charbunny'},
            {h.name for h in Headset.objects.all()},
            'Wrong set of names',
        )
        run = SpeedRun.objects.get(name='Test Run', event__short='test')
        self.assertSequenceEqual(['puwexil'], [r.name for r in run.runners.all()])
        self.assertSequenceEqual(
            ['SpikeVegeta'], [c.name for c in run.commentators.all()]
        )
        self.assertSequenceEqual(['Charbunny'], [h.name for h in run.hosts.all()])
