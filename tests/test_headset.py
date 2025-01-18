from .util import MigrationsTestCase, today_noon

# historical only, Headsets and Runners have been merged into Talent since this was written


# noinspection PyPep8Naming
class TestHostMigration(MigrationsTestCase):
    migrate_from = [('tracker', '0026_add_hosts_commentators')]
    migrate_to = [('tracker', '0027_migrate_hosts')]

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        SpeedRun = apps.get_model('tracker', 'SpeedRun')
        HostSlot = apps.get_model('tracker', 'HostSlot')
        self.event = Event.objects.create(
            short='test',
            name='Test Event',
            datetime=today_noon,
        )
        self.run1 = SpeedRun.objects.create(
            event=self.event, name='Test Run 1', order=1, run_time='0:05:00'
        )
        self.run2 = SpeedRun.objects.create(
            event=self.event, name='Test Run 2', order=2, run_time='0:05:00'
        )
        self.run3 = SpeedRun.objects.create(
            event=self.event, name='Test Run 3', order=3, run_time='0:05:00'
        )
        self.hostname = 'Mr. Game and Shout, Prolix'
        self.hostslot = HostSlot.objects.create(
            start_run=self.run1, end_run=self.run3, name=self.hostname
        )

    def test_migrated(self):
        SpeedRun = self.apps.get_model('tracker', 'SpeedRun')
        Headset = self.apps.get_model('tracker', 'Headset')
        for run in SpeedRun.objects.all():
            with self.subTest(run.name):
                self.assertEqual(
                    [self.hostname],
                    [', '.join(h.name for h in run.hosts.all())],
                    msg=f'Run #{run.order} had incorrect hosts',
                )
                self.assertEqual(
                    run.hosts.count(), 2, msg='Host name did not get split'
                )
        self.assertEqual(Headset.objects.count(), 2, msg='Incorrect number of Headsets')


# noinspection PyPep8Naming
class TestHostMigrationReverse(MigrationsTestCase):
    migrate_from = [('tracker', '0027_migrate_hosts')]
    migrate_to = [('tracker', '0026_add_hosts_commentators')]

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        SpeedRun = apps.get_model('tracker', 'SpeedRun')
        Headset = apps.get_model('tracker', 'Headset')
        self.event = Event.objects.create(
            short='test', name='Test Event', datetime=today_noon, targetamount=100
        )
        self.headsets = [
            Headset.objects.create(name='Mr. Game and Shout'),
            Headset.objects.create(name='Prolix'),
        ]
        self.run1 = SpeedRun.objects.create(
            event=self.event, name='Test Run 1', order=1, run_time='0:05:00'
        )
        self.run2 = SpeedRun.objects.create(
            event=self.event, name='Test Run 2', order=2, run_time='0:05:00'
        )
        self.run3 = SpeedRun.objects.create(
            event=self.event, name='Test Run 3', order=3, run_time='0:05:00'
        )
        for run in [self.run1, self.run2, self.run3]:
            run.hosts.set(self.headsets)

    def test_migrated(self):
        SpeedRun = self.apps.get_model('tracker', 'SpeedRun')
        HostSlot = self.apps.get_model('tracker', 'HostSlot')
        for run in SpeedRun.objects.all():
            with self.subTest(run.name):
                self.assertEqual(
                    HostSlot.objects.get(start_run=run).name,
                    ', '.join(h.name for h in self.headsets),
                    msg=f'Host Slot for #{run.order} did not match',
                )


# noinspection PyPep8Naming
class TestHeadsetCaseMergeMigration(MigrationsTestCase):
    migrate_from = [('tracker', '0028_delete_host_slots')]
    migrate_to = [('tracker', '0029_headset_merge_case')]

    def setUpBeforeMigration(self, apps):
        Event = apps.get_model('tracker', 'Event')
        SpeedRun = apps.get_model('tracker', 'SpeedRun')
        Headset = apps.get_model('tracker', 'Headset')
        self.event = Event.objects.create(
            short='test', name='Test Event', datetime=today_noon, targetamount=100
        )
        self.run1 = SpeedRun.objects.create(
            event=self.event, name='Test Run 1', order=1, run_time='0:05:00'
        )
        self.run2 = SpeedRun.objects.create(
            event=self.event, name='Test Run 2', order=2, run_time='0:05:00'
        )
        self.run3 = SpeedRun.objects.create(
            event=self.event, name='Test Run 3', order=3, run_time='0:05:00'
        )
        headset1 = Headset.objects.create(name='KungFuFruitCup')
        headset2 = Headset.objects.create(name='Kungfufruitcup')
        headset3 = Headset.objects.create(name='Prolix')
        self.run1.hosts.add(headset1)
        self.run2.hosts.add(headset2)
        self.run3.hosts.add(headset3)
        self.run3.commentators.add(headset2)

    def test_migrated(self):
        SpeedRun = self.apps.get_model('tracker', 'SpeedRun')
        HeadSet = self.apps.get_model('tracker', 'Headset')
        self.assertEqual(HeadSet.objects.count(), 2)
        self.assertEqual(
            SpeedRun.objects.get(pk=self.run1.id).hosts.first().name, 'KungFuFruitCup'
        )
        self.assertEqual(
            SpeedRun.objects.get(pk=self.run2.id).hosts.first().name, 'KungFuFruitCup'
        )
        self.assertEqual(
            SpeedRun.objects.get(pk=self.run3.id).hosts.first().name, 'Prolix'
        )
        self.assertEqual(
            SpeedRun.objects.get(pk=self.run3.id).commentators.first().name,
            'KungFuFruitCup',
        )
