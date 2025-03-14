# Generated by Django 5.1 on 2024-08-23 23:18

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0040_add_interstitial_anchor'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='log',
            options={'ordering': ['-timestamp'], 'verbose_name': 'Log'},
        ),
        migrations.AlterModelOptions(
            name='userprofile',
            options={
                'permissions': (
                    ('show_queries', 'Can view database queries'),
                    ('can_search_for_user', 'Can use User lookup endpoint'),
                ),
                'verbose_name': 'User Profile',
            },
        ),
        migrations.AlterModelOptions(
            name='donor',
            options={
                'ordering': ['lastname', 'firstname', 'email'],
                'permissions': (
                    ('delete_all_donors', 'Can delete donors with cleared donations'),
                    ('view_full_names', 'Can search for donors by full name'),
                    ('view_emails', 'Can search for donors by email address'),
                ),
            },
        ),
        migrations.AlterModelOptions(
            name='donation',
            options={
                'get_latest_by': 'timereceived',
                'ordering': ['-timereceived'],
                'permissions': (
                    ('delete_all_donations', 'Can delete non-local donations'),
                    ('view_comments', 'Can view all comments'),
                    ('view_pending_donation', 'Can view pending donations'),
                    ('view_test', 'Can view test donations'),
                    ('send_to_reader', 'Can send donations to the reader'),
                ),
            },
        ),
    ]
