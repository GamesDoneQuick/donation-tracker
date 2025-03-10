# Generated by Django 5.1 on 2024-09-30 20:14

from django.db import migrations, OperationalError


def merge_runner_and_headset(apps, schema_editor):
    Runner = apps.get_model('tracker', 'Runner')
    Headset = apps.get_model('tracker', 'Headset')
    for headset in Headset.objects.select_related('runner').prefetch_related('hosting_for', 'commentating_for'):
        if headset.runner is None:
            headset.runner = Runner.objects.get_or_create(
                name__iexact=headset.name,
                defaults={'name': headset.name}
            )[0]
            headset.save()
        if headset.runner.pronouns.strip() == '':
            headset.runner.pronouns = headset.pronouns.strip()
            headset.runner.save()
        for run in headset.hosting_for.all():
            run.thosts.add(headset.runner)
        for run in headset.commentating_for.all():
            run.tcommentators.add(headset.runner)


def unmerge_runner_and_headset(apps, schema_editor):
    Run = apps.get_model('tracker', 'SpeedRun')
    Headset = apps.get_model('tracker', 'Headset')
    for run in Run.objects.prefetch_related('thosts', 'tcommentators'):
        # not the most efficient but if this migration is getting reversed something probably already went wrong
        for h in run.thosts.all():
            run.hosts.add(
                Headset.objects.get_or_create(
                    name=h.name,
                    defaults={
                        'pronouns': h.pronouns,
                        'runner': h,
                    })[0]
            )
        for c in run.tcommentators.all():
            run.commentators.add(
                Headset.objects.get_or_create(
                    name=c.name,
                    defaults={
                        'pronouns': c.pronouns,
                        'runner': c,
                    })[0]
            )


class Migration(migrations.Migration):
    dependencies = [
        ('tracker', '0044_add_new_talent_fields'),
    ]

    operations = [
        migrations.RunPython(merge_runner_and_headset, unmerge_runner_and_headset, elidable=True),
    ]
