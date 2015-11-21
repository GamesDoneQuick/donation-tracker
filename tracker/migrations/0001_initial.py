# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import tracker.validators
import tracker.models.donation
import mptt.fields
import tracker.models.event
import django.db.models.deletion
from decimal import Decimal
import tracker.models.prize
import oauth2client.django_orm
import django.utils.timezone
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('post_office', '__first__'),
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Bid',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('state', models.CharField(default=b'OPENED', max_length=32, choices=[(b'PENDING', b'Pending'), (b'DENIED', b'Denied'), (b'HIDDEN', b'Hidden'), (b'OPENED', b'Opened'), (b'CLOSED', b'Closed')])),
                ('description', models.TextField(max_length=1024, blank=True)),
                ('shortdescription', models.TextField(help_text=b'Alternative description text to display in tight spaces', max_length=256, verbose_name=b'Short Description', blank=True)),
                ('goal', models.DecimalField(default=None, null=True, max_digits=20, decimal_places=2, blank=True)),
                ('istarget', models.BooleanField(default=False, help_text=b"Set this if this bid is a 'target' for donations (bottom level choice or challenge)", verbose_name=b'Target')),
                ('allowuseroptions', models.BooleanField(default=False, help_text=b'If set, this will allow donors to specify their own options on the donate page (pending moderator approval)', verbose_name=b'Allow User Options')),
                ('revealedtime', models.DateTimeField(null=True, verbose_name=b'Revealed Time', blank=True)),
                ('total', models.DecimalField(default=Decimal('0.00'), editable=False, max_digits=20, decimal_places=2)),
                ('count', models.IntegerField(editable=False)),
                ('lft', models.PositiveIntegerField(editable=False, db_index=True)),
                ('rght', models.PositiveIntegerField(editable=False, db_index=True)),
                ('tree_id', models.PositiveIntegerField(editable=False, db_index=True)),
                ('level', models.PositiveIntegerField(editable=False, db_index=True)),
                ('biddependency', models.ForeignKey(related_name='depedent_bids', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Dependency', blank=True, to='tracker.Bid', null=True)),
            ],
            options={
                'ordering': ['event__date', 'speedrun__starttime', 'parent__name', 'name'],
                'permissions': (('top_level_bid', 'Can create new top level bids'), ('delete_all_bids', 'Can delete bids with donations attached'), ('view_hidden', 'Can view hidden bids')),
            },
        ),
        migrations.CreateModel(
            name='BidSuggestion',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64, verbose_name=b'Name')),
                ('bid', models.ForeignKey(related_name='suggestions', on_delete=django.db.models.deletion.PROTECT, to='tracker.Bid')),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='CredentialsModel',
            fields=[
                ('id', models.ForeignKey(primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('credentials', oauth2client.django_orm.CredentialsField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Donation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('domain', models.CharField(default=b'LOCAL', max_length=255, choices=[(b'LOCAL', b'Local'), (b'CHIPIN', b'ChipIn'), (b'PAYPAL', b'PayPal')])),
                ('domainId', models.CharField(unique=True, max_length=160, editable=False, blank=True)),
                ('transactionstate', models.CharField(default=b'PENDING', max_length=64, verbose_name=b'Transaction State', choices=[(b'PENDING', b'Pending'), (b'COMPLETED', b'Completed'), (b'CANCELLED', b'Cancelled'), (b'FLAGGED', b'Flagged')])),
                ('bidstate', models.CharField(default=b'PENDING', max_length=255, verbose_name=b'Bid State', choices=[(b'PENDING', b'Pending'), (b'IGNORED', b'Ignored'), (b'PROCESSED', b'Processed'), (b'FLAGGED', b'Flagged')])),
                ('readstate', models.CharField(default=b'PENDING', max_length=255, verbose_name=b'Read State', choices=[(b'PENDING', b'Pending'), (b'READY', b'Ready to Read'), (b'IGNORED', b'Ignored'), (b'READ', b'Read'), (b'FLAGGED', b'Flagged')])),
                ('commentstate', models.CharField(default=b'ABSENT', max_length=255, verbose_name=b'Comment State', choices=[(b'ABSENT', b'Absent'), (b'PENDING', b'Pending'), (b'DENIED', b'Denied'), (b'APPROVED', b'Approved'), (b'FLAGGED', b'Flagged')])),
                ('amount', models.DecimalField(default=Decimal('0.00'), verbose_name=b'Donation Amount', max_digits=20, decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('fee', models.DecimalField(default=Decimal('0.00'), verbose_name=b'Donation Fee', max_digits=20, decimal_places=2, validators=[tracker.validators.positive])),
                ('currency', models.CharField(max_length=8, verbose_name=b'Currency', choices=[(b'USD', b'US Dollars'), (b'CAD', b'Canadian Dollars')])),
                ('timereceived', models.DateTimeField(default=django.utils.timezone.now, verbose_name=b'Time Received')),
                ('comment', models.TextField(verbose_name=b'Comment', blank=True)),
                ('modcomment', models.TextField(verbose_name=b'Moderator Comment', blank=True)),
                ('testdonation', models.BooleanField(default=False)),
                ('requestedvisibility', models.CharField(default=b'CURR', max_length=32, verbose_name=b'Requested Visibility', choices=[(b'CURR', b'Use Existing (Anonymous if not set)'), (b'FULL', b'Fully Visible'), (b'FIRST', b'First Name, Last Initial'), (b'ALIAS', b'Alias Only'), (b'ANON', b'Anonymous')])),
                ('requestedalias', models.CharField(max_length=32, null=True, verbose_name=b'Requested Alias', blank=True)),
                ('requestedemail', models.EmailField(max_length=128, null=True, verbose_name=b'Requested Contact Email', blank=True)),
                ('commentlanguage', models.CharField(default=b'un', max_length=32, verbose_name=b'Comment Language', choices=[(b'un', b'Unknown'), (b'en', b'English'), (b'fr', b'French'), (b'de', b'German')])),
            ],
            options={
                'ordering': ['-timereceived'],
                'get_latest_by': 'timereceived',
                'permissions': (('delete_all_donations', 'Can delete non-local donations'), ('view_full_list', 'Can view full donation list'), ('view_comments', 'Can view all comments'), ('view_pending', 'Can view pending donations'), ('view_test', 'Can view test donations'), ('send_to_reader', 'Can send donations to the reader')),
            },
        ),
        migrations.CreateModel(
            name='DonationBid',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=20, decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('bid', models.ForeignKey(related_name='bids', on_delete=django.db.models.deletion.PROTECT, to='tracker.Bid')),
                ('donation', models.ForeignKey(related_name='bids', on_delete=django.db.models.deletion.PROTECT, to='tracker.Donation')),
            ],
            options={
                'ordering': ['-donation__timereceived'],
                'verbose_name': 'Donation Bid',
            },
        ),
        migrations.CreateModel(
            name='Donor',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('email', models.EmailField(max_length=128, verbose_name=b'Contact Email')),
                ('alias', models.CharField(max_length=32, null=True, blank=True)),
                ('firstname', models.CharField(max_length=64, verbose_name=b'First Name', blank=True)),
                ('lastname', models.CharField(max_length=64, verbose_name=b'Last Name', blank=True)),
                ('visibility', models.CharField(default=b'FIRST', max_length=32, choices=[(b'FULL', b'Fully Visible'), (b'FIRST', b'First Name, Last Initial'), (b'ALIAS', b'Alias Only'), (b'ANON', b'Anonymous')])),
                ('addresscity', models.CharField(max_length=128, verbose_name=b'City', blank=True)),
                ('addressstreet', models.CharField(max_length=128, verbose_name=b'Street/P.O. Box', blank=True)),
                ('addressstate', models.CharField(max_length=128, verbose_name=b'State/Province', blank=True)),
                ('addresszip', models.CharField(max_length=128, verbose_name=b'Zip/Postal Code', blank=True)),
                ('addresscountry', models.CharField(max_length=128, verbose_name=b'Country', blank=True)),
                ('paypalemail', models.EmailField(max_length=128, unique=True, null=True, verbose_name=b'Paypal Email', blank=True)),
                ('runneryoutube', models.CharField(max_length=128, unique=True, null=True, verbose_name=b'Youtube Account', blank=True)),
                ('runnertwitch', models.CharField(max_length=128, unique=True, null=True, verbose_name=b'Twitch Account', blank=True)),
                ('runnertwitter', models.CharField(max_length=128, unique=True, null=True, verbose_name=b'Twitter Account', blank=True)),
            ],
            options={
                'ordering': ['lastname', 'firstname', 'email'],
                'permissions': (('delete_all_donors', 'Can delete donors with cleared donations'), ('view_usernames', 'Can view full usernames'), ('view_emails', 'Can view email addresses')),
            },
        ),
        migrations.CreateModel(
            name='DonorCache',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('donation_total', models.DecimalField(default=0, editable=False, max_digits=20, decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('donation_count', models.IntegerField(default=0, editable=False, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('donation_avg', models.DecimalField(default=0, editable=False, max_digits=20, decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('donation_max', models.DecimalField(default=0, editable=False, max_digits=20, decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('donor', models.ForeignKey(to='tracker.Donor')),
            ],
            options={
                'ordering': ('donor',),
            },
        ),
        migrations.CreateModel(
            name='DonorPrizeEntry',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('weight', models.DecimalField(decimal_places=2, default=Decimal('1.0'), max_digits=20, validators=[tracker.validators.positive, tracker.validators.nonzero], help_text=b'This is the weight to apply this entry in the drawing (if weight is applicable).', verbose_name=b'Entry Weight')),
                ('donor', models.ForeignKey(to='tracker.Donor', on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={
                'verbose_name': 'Donor Prize Entry',
                'verbose_name_plural': 'Donor Prize Entries',
            },
        ),
        migrations.CreateModel(
            name='Event',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('short', models.CharField(unique=True, max_length=64)),
                ('name', models.CharField(max_length=128)),
                ('receivername', models.CharField(max_length=128, verbose_name=b'Receiver Name', blank=True)),
                ('targetamount', models.DecimalField(verbose_name=b'Target Amount', max_digits=20, decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('usepaypalsandbox', models.BooleanField(default=False, verbose_name=b'Use Paypal Sandbox')),
                ('paypalemail', models.EmailField(max_length=128, verbose_name=b'Receiver Paypal')),
                ('paypalcurrency', models.CharField(default=b'USD', max_length=8, verbose_name=b'Currency', choices=[(b'USD', b'US Dollars'), (b'CAD', b'Canadian Dollars')])),
                ('donationemailsender', models.EmailField(max_length=128, null=True, verbose_name=b'Donation Email Sender', blank=True)),
                ('scheduleid', models.CharField(max_length=128, unique=True, null=True, verbose_name=b'Schedule ID', blank=True)),
                ('scheduletimezone', models.CharField(default=b'US/Eastern', max_length=64, verbose_name=b'Schedule Timezone', blank=True, choices=[(b'Africa/Abidjan', b'Africa/Abidjan'), (b'Africa/Accra', b'Africa/Accra'), (b'Africa/Addis_Ababa', b'Africa/Addis_Ababa'), (b'Africa/Algiers', b'Africa/Algiers'), (b'Africa/Asmara', b'Africa/Asmara'), (b'Africa/Bamako', b'Africa/Bamako'), (b'Africa/Bangui', b'Africa/Bangui'), (b'Africa/Banjul', b'Africa/Banjul'), (b'Africa/Bissau', b'Africa/Bissau'), (b'Africa/Blantyre', b'Africa/Blantyre'), (b'Africa/Brazzaville', b'Africa/Brazzaville'), (b'Africa/Bujumbura', b'Africa/Bujumbura'), (b'Africa/Cairo', b'Africa/Cairo'), (b'Africa/Casablanca', b'Africa/Casablanca'), (b'Africa/Ceuta', b'Africa/Ceuta'), (b'Africa/Conakry', b'Africa/Conakry'), (b'Africa/Dakar', b'Africa/Dakar'), (b'Africa/Dar_es_Salaam', b'Africa/Dar_es_Salaam'), (b'Africa/Djibouti', b'Africa/Djibouti'), (b'Africa/Douala', b'Africa/Douala'), (b'Africa/El_Aaiun', b'Africa/El_Aaiun'), (b'Africa/Freetown', b'Africa/Freetown'), (b'Africa/Gaborone', b'Africa/Gaborone'), (b'Africa/Harare', b'Africa/Harare'), (b'Africa/Johannesburg', b'Africa/Johannesburg'), (b'Africa/Juba', b'Africa/Juba'), (b'Africa/Kampala', b'Africa/Kampala'), (b'Africa/Khartoum', b'Africa/Khartoum'), (b'Africa/Kigali', b'Africa/Kigali'), (b'Africa/Kinshasa', b'Africa/Kinshasa'), (b'Africa/Lagos', b'Africa/Lagos'), (b'Africa/Libreville', b'Africa/Libreville'), (b'Africa/Lome', b'Africa/Lome'), (b'Africa/Luanda', b'Africa/Luanda'), (b'Africa/Lubumbashi', b'Africa/Lubumbashi'), (b'Africa/Lusaka', b'Africa/Lusaka'), (b'Africa/Malabo', b'Africa/Malabo'), (b'Africa/Maputo', b'Africa/Maputo'), (b'Africa/Maseru', b'Africa/Maseru'), (b'Africa/Mbabane', b'Africa/Mbabane'), (b'Africa/Mogadishu', b'Africa/Mogadishu'), (b'Africa/Monrovia', b'Africa/Monrovia'), (b'Africa/Nairobi', b'Africa/Nairobi'), (b'Africa/Ndjamena', b'Africa/Ndjamena'), (b'Africa/Niamey', b'Africa/Niamey'), (b'Africa/Nouakchott', b'Africa/Nouakchott'), (b'Africa/Ouagadougou', b'Africa/Ouagadougou'), (b'Africa/Porto-Novo', b'Africa/Porto-Novo'), (b'Africa/Sao_Tome', b'Africa/Sao_Tome'), (b'Africa/Tripoli', b'Africa/Tripoli'), (b'Africa/Tunis', b'Africa/Tunis'), (b'Africa/Windhoek', b'Africa/Windhoek'), (b'America/Adak', b'America/Adak'), (b'America/Anchorage', b'America/Anchorage'), (b'America/Anguilla', b'America/Anguilla'), (b'America/Antigua', b'America/Antigua'), (b'America/Araguaina', b'America/Araguaina'), (b'America/Argentina/Buenos_Aires', b'America/Argentina/Buenos_Aires'), (b'America/Argentina/Catamarca', b'America/Argentina/Catamarca'), (b'America/Argentina/Cordoba', b'America/Argentina/Cordoba'), (b'America/Argentina/Jujuy', b'America/Argentina/Jujuy'), (b'America/Argentina/La_Rioja', b'America/Argentina/La_Rioja'), (b'America/Argentina/Mendoza', b'America/Argentina/Mendoza'), (b'America/Argentina/Rio_Gallegos', b'America/Argentina/Rio_Gallegos'), (b'America/Argentina/Salta', b'America/Argentina/Salta'), (b'America/Argentina/San_Juan', b'America/Argentina/San_Juan'), (b'America/Argentina/San_Luis', b'America/Argentina/San_Luis'), (b'America/Argentina/Tucuman', b'America/Argentina/Tucuman'), (b'America/Argentina/Ushuaia', b'America/Argentina/Ushuaia'), (b'America/Aruba', b'America/Aruba'), (b'America/Asuncion', b'America/Asuncion'), (b'America/Atikokan', b'America/Atikokan'), (b'America/Bahia', b'America/Bahia'), (b'America/Bahia_Banderas', b'America/Bahia_Banderas'), (b'America/Barbados', b'America/Barbados'), (b'America/Belem', b'America/Belem'), (b'America/Belize', b'America/Belize'), (b'America/Blanc-Sablon', b'America/Blanc-Sablon'), (b'America/Boa_Vista', b'America/Boa_Vista'), (b'America/Bogota', b'America/Bogota'), (b'America/Boise', b'America/Boise'), (b'America/Cambridge_Bay', b'America/Cambridge_Bay'), (b'America/Campo_Grande', b'America/Campo_Grande'), (b'America/Cancun', b'America/Cancun'), (b'America/Caracas', b'America/Caracas'), (b'America/Cayenne', b'America/Cayenne'), (b'America/Cayman', b'America/Cayman'), (b'America/Chicago', b'America/Chicago'), (b'America/Chihuahua', b'America/Chihuahua'), (b'America/Costa_Rica', b'America/Costa_Rica'), (b'America/Creston', b'America/Creston'), (b'America/Cuiaba', b'America/Cuiaba'), (b'America/Curacao', b'America/Curacao'), (b'America/Danmarkshavn', b'America/Danmarkshavn'), (b'America/Dawson', b'America/Dawson'), (b'America/Dawson_Creek', b'America/Dawson_Creek'), (b'America/Denver', b'America/Denver'), (b'America/Detroit', b'America/Detroit'), (b'America/Dominica', b'America/Dominica'), (b'America/Edmonton', b'America/Edmonton'), (b'America/Eirunepe', b'America/Eirunepe'), (b'America/El_Salvador', b'America/El_Salvador'), (b'America/Fortaleza', b'America/Fortaleza'), (b'America/Glace_Bay', b'America/Glace_Bay'), (b'America/Godthab', b'America/Godthab'), (b'America/Goose_Bay', b'America/Goose_Bay'), (b'America/Grand_Turk', b'America/Grand_Turk'), (b'America/Grenada', b'America/Grenada'), (b'America/Guadeloupe', b'America/Guadeloupe'), (b'America/Guatemala', b'America/Guatemala'), (b'America/Guayaquil', b'America/Guayaquil'), (b'America/Guyana', b'America/Guyana'), (b'America/Halifax', b'America/Halifax'), (b'America/Havana', b'America/Havana'), (b'America/Hermosillo', b'America/Hermosillo'), (b'America/Indiana/Indianapolis', b'America/Indiana/Indianapolis'), (b'America/Indiana/Knox', b'America/Indiana/Knox'), (b'America/Indiana/Marengo', b'America/Indiana/Marengo'), (b'America/Indiana/Petersburg', b'America/Indiana/Petersburg'), (b'America/Indiana/Tell_City', b'America/Indiana/Tell_City'), (b'America/Indiana/Vevay', b'America/Indiana/Vevay'), (b'America/Indiana/Vincennes', b'America/Indiana/Vincennes'), (b'America/Indiana/Winamac', b'America/Indiana/Winamac'), (b'America/Inuvik', b'America/Inuvik'), (b'America/Iqaluit', b'America/Iqaluit'), (b'America/Jamaica', b'America/Jamaica'), (b'America/Juneau', b'America/Juneau'), (b'America/Kentucky/Louisville', b'America/Kentucky/Louisville'), (b'America/Kentucky/Monticello', b'America/Kentucky/Monticello'), (b'America/Kralendijk', b'America/Kralendijk'), (b'America/La_Paz', b'America/La_Paz'), (b'America/Lima', b'America/Lima'), (b'America/Los_Angeles', b'America/Los_Angeles'), (b'America/Lower_Princes', b'America/Lower_Princes'), (b'America/Maceio', b'America/Maceio'), (b'America/Managua', b'America/Managua'), (b'America/Manaus', b'America/Manaus'), (b'America/Marigot', b'America/Marigot'), (b'America/Martinique', b'America/Martinique'), (b'America/Matamoros', b'America/Matamoros'), (b'America/Mazatlan', b'America/Mazatlan'), (b'America/Menominee', b'America/Menominee'), (b'America/Merida', b'America/Merida'), (b'America/Metlakatla', b'America/Metlakatla'), (b'America/Mexico_City', b'America/Mexico_City'), (b'America/Miquelon', b'America/Miquelon'), (b'America/Moncton', b'America/Moncton'), (b'America/Monterrey', b'America/Monterrey'), (b'America/Montevideo', b'America/Montevideo'), (b'America/Montserrat', b'America/Montserrat'), (b'America/Nassau', b'America/Nassau'), (b'America/New_York', b'America/New_York'), (b'America/Nipigon', b'America/Nipigon'), (b'America/Nome', b'America/Nome'), (b'America/Noronha', b'America/Noronha'), (b'America/North_Dakota/Beulah', b'America/North_Dakota/Beulah'), (b'America/North_Dakota/Center', b'America/North_Dakota/Center'), (b'America/North_Dakota/New_Salem', b'America/North_Dakota/New_Salem'), (b'America/Ojinaga', b'America/Ojinaga'), (b'America/Panama', b'America/Panama'), (b'America/Pangnirtung', b'America/Pangnirtung'), (b'America/Paramaribo', b'America/Paramaribo'), (b'America/Phoenix', b'America/Phoenix'), (b'America/Port-au-Prince', b'America/Port-au-Prince'), (b'America/Port_of_Spain', b'America/Port_of_Spain'), (b'America/Porto_Velho', b'America/Porto_Velho'), (b'America/Puerto_Rico', b'America/Puerto_Rico'), (b'America/Rainy_River', b'America/Rainy_River'), (b'America/Rankin_Inlet', b'America/Rankin_Inlet'), (b'America/Recife', b'America/Recife'), (b'America/Regina', b'America/Regina'), (b'America/Resolute', b'America/Resolute'), (b'America/Rio_Branco', b'America/Rio_Branco'), (b'America/Santa_Isabel', b'America/Santa_Isabel'), (b'America/Santarem', b'America/Santarem'), (b'America/Santiago', b'America/Santiago'), (b'America/Santo_Domingo', b'America/Santo_Domingo'), (b'America/Sao_Paulo', b'America/Sao_Paulo'), (b'America/Scoresbysund', b'America/Scoresbysund'), (b'America/Sitka', b'America/Sitka'), (b'America/St_Barthelemy', b'America/St_Barthelemy'), (b'America/St_Johns', b'America/St_Johns'), (b'America/St_Kitts', b'America/St_Kitts'), (b'America/St_Lucia', b'America/St_Lucia'), (b'America/St_Thomas', b'America/St_Thomas'), (b'America/St_Vincent', b'America/St_Vincent'), (b'America/Swift_Current', b'America/Swift_Current'), (b'America/Tegucigalpa', b'America/Tegucigalpa'), (b'America/Thule', b'America/Thule'), (b'America/Thunder_Bay', b'America/Thunder_Bay'), (b'America/Tijuana', b'America/Tijuana'), (b'America/Toronto', b'America/Toronto'), (b'America/Tortola', b'America/Tortola'), (b'America/Vancouver', b'America/Vancouver'), (b'America/Whitehorse', b'America/Whitehorse'), (b'America/Winnipeg', b'America/Winnipeg'), (b'America/Yakutat', b'America/Yakutat'), (b'America/Yellowknife', b'America/Yellowknife'), (b'Antarctica/Casey', b'Antarctica/Casey'), (b'Antarctica/Davis', b'Antarctica/Davis'), (b'Antarctica/DumontDUrville', b'Antarctica/DumontDUrville'), (b'Antarctica/Macquarie', b'Antarctica/Macquarie'), (b'Antarctica/Mawson', b'Antarctica/Mawson'), (b'Antarctica/McMurdo', b'Antarctica/McMurdo'), (b'Antarctica/Palmer', b'Antarctica/Palmer'), (b'Antarctica/Rothera', b'Antarctica/Rothera'), (b'Antarctica/Syowa', b'Antarctica/Syowa'), (b'Antarctica/Troll', b'Antarctica/Troll'), (b'Antarctica/Vostok', b'Antarctica/Vostok'), (b'Arctic/Longyearbyen', b'Arctic/Longyearbyen'), (b'Asia/Aden', b'Asia/Aden'), (b'Asia/Almaty', b'Asia/Almaty'), (b'Asia/Amman', b'Asia/Amman'), (b'Asia/Anadyr', b'Asia/Anadyr'), (b'Asia/Aqtau', b'Asia/Aqtau'), (b'Asia/Aqtobe', b'Asia/Aqtobe'), (b'Asia/Ashgabat', b'Asia/Ashgabat'), (b'Asia/Baghdad', b'Asia/Baghdad'), (b'Asia/Bahrain', b'Asia/Bahrain'), (b'Asia/Baku', b'Asia/Baku'), (b'Asia/Bangkok', b'Asia/Bangkok'), (b'Asia/Beirut', b'Asia/Beirut'), (b'Asia/Bishkek', b'Asia/Bishkek'), (b'Asia/Brunei', b'Asia/Brunei'), (b'Asia/Chita', b'Asia/Chita'), (b'Asia/Choibalsan', b'Asia/Choibalsan'), (b'Asia/Colombo', b'Asia/Colombo'), (b'Asia/Damascus', b'Asia/Damascus'), (b'Asia/Dhaka', b'Asia/Dhaka'), (b'Asia/Dili', b'Asia/Dili'), (b'Asia/Dubai', b'Asia/Dubai'), (b'Asia/Dushanbe', b'Asia/Dushanbe'), (b'Asia/Gaza', b'Asia/Gaza'), (b'Asia/Hebron', b'Asia/Hebron'), (b'Asia/Ho_Chi_Minh', b'Asia/Ho_Chi_Minh'), (b'Asia/Hong_Kong', b'Asia/Hong_Kong'), (b'Asia/Hovd', b'Asia/Hovd'), (b'Asia/Irkutsk', b'Asia/Irkutsk'), (b'Asia/Jakarta', b'Asia/Jakarta'), (b'Asia/Jayapura', b'Asia/Jayapura'), (b'Asia/Jerusalem', b'Asia/Jerusalem'), (b'Asia/Kabul', b'Asia/Kabul'), (b'Asia/Kamchatka', b'Asia/Kamchatka'), (b'Asia/Karachi', b'Asia/Karachi'), (b'Asia/Kathmandu', b'Asia/Kathmandu'), (b'Asia/Khandyga', b'Asia/Khandyga'), (b'Asia/Kolkata', b'Asia/Kolkata'), (b'Asia/Krasnoyarsk', b'Asia/Krasnoyarsk'), (b'Asia/Kuala_Lumpur', b'Asia/Kuala_Lumpur'), (b'Asia/Kuching', b'Asia/Kuching'), (b'Asia/Kuwait', b'Asia/Kuwait'), (b'Asia/Macau', b'Asia/Macau'), (b'Asia/Magadan', b'Asia/Magadan'), (b'Asia/Makassar', b'Asia/Makassar'), (b'Asia/Manila', b'Asia/Manila'), (b'Asia/Muscat', b'Asia/Muscat'), (b'Asia/Nicosia', b'Asia/Nicosia'), (b'Asia/Novokuznetsk', b'Asia/Novokuznetsk'), (b'Asia/Novosibirsk', b'Asia/Novosibirsk'), (b'Asia/Omsk', b'Asia/Omsk'), (b'Asia/Oral', b'Asia/Oral'), (b'Asia/Phnom_Penh', b'Asia/Phnom_Penh'), (b'Asia/Pontianak', b'Asia/Pontianak'), (b'Asia/Pyongyang', b'Asia/Pyongyang'), (b'Asia/Qatar', b'Asia/Qatar'), (b'Asia/Qyzylorda', b'Asia/Qyzylorda'), (b'Asia/Rangoon', b'Asia/Rangoon'), (b'Asia/Riyadh', b'Asia/Riyadh'), (b'Asia/Sakhalin', b'Asia/Sakhalin'), (b'Asia/Samarkand', b'Asia/Samarkand'), (b'Asia/Seoul', b'Asia/Seoul'), (b'Asia/Shanghai', b'Asia/Shanghai'), (b'Asia/Singapore', b'Asia/Singapore'), (b'Asia/Srednekolymsk', b'Asia/Srednekolymsk'), (b'Asia/Taipei', b'Asia/Taipei'), (b'Asia/Tashkent', b'Asia/Tashkent'), (b'Asia/Tbilisi', b'Asia/Tbilisi'), (b'Asia/Tehran', b'Asia/Tehran'), (b'Asia/Thimphu', b'Asia/Thimphu'), (b'Asia/Tokyo', b'Asia/Tokyo'), (b'Asia/Ulaanbaatar', b'Asia/Ulaanbaatar'), (b'Asia/Urumqi', b'Asia/Urumqi'), (b'Asia/Ust-Nera', b'Asia/Ust-Nera'), (b'Asia/Vientiane', b'Asia/Vientiane'), (b'Asia/Vladivostok', b'Asia/Vladivostok'), (b'Asia/Yakutsk', b'Asia/Yakutsk'), (b'Asia/Yekaterinburg', b'Asia/Yekaterinburg'), (b'Asia/Yerevan', b'Asia/Yerevan'), (b'Atlantic/Azores', b'Atlantic/Azores'), (b'Atlantic/Bermuda', b'Atlantic/Bermuda'), (b'Atlantic/Canary', b'Atlantic/Canary'), (b'Atlantic/Cape_Verde', b'Atlantic/Cape_Verde'), (b'Atlantic/Faroe', b'Atlantic/Faroe'), (b'Atlantic/Madeira', b'Atlantic/Madeira'), (b'Atlantic/Reykjavik', b'Atlantic/Reykjavik'), (b'Atlantic/South_Georgia', b'Atlantic/South_Georgia'), (b'Atlantic/St_Helena', b'Atlantic/St_Helena'), (b'Atlantic/Stanley', b'Atlantic/Stanley'), (b'Australia/Adelaide', b'Australia/Adelaide'), (b'Australia/Brisbane', b'Australia/Brisbane'), (b'Australia/Broken_Hill', b'Australia/Broken_Hill'), (b'Australia/Currie', b'Australia/Currie'), (b'Australia/Darwin', b'Australia/Darwin'), (b'Australia/Eucla', b'Australia/Eucla'), (b'Australia/Hobart', b'Australia/Hobart'), (b'Australia/Lindeman', b'Australia/Lindeman'), (b'Australia/Lord_Howe', b'Australia/Lord_Howe'), (b'Australia/Melbourne', b'Australia/Melbourne'), (b'Australia/Perth', b'Australia/Perth'), (b'Australia/Sydney', b'Australia/Sydney'), (b'Canada/Atlantic', b'Canada/Atlantic'), (b'Canada/Central', b'Canada/Central'), (b'Canada/Eastern', b'Canada/Eastern'), (b'Canada/Mountain', b'Canada/Mountain'), (b'Canada/Newfoundland', b'Canada/Newfoundland'), (b'Canada/Pacific', b'Canada/Pacific'), (b'Europe/Amsterdam', b'Europe/Amsterdam'), (b'Europe/Andorra', b'Europe/Andorra'), (b'Europe/Athens', b'Europe/Athens'), (b'Europe/Belgrade', b'Europe/Belgrade'), (b'Europe/Berlin', b'Europe/Berlin'), (b'Europe/Bratislava', b'Europe/Bratislava'), (b'Europe/Brussels', b'Europe/Brussels'), (b'Europe/Bucharest', b'Europe/Bucharest'), (b'Europe/Budapest', b'Europe/Budapest'), (b'Europe/Busingen', b'Europe/Busingen'), (b'Europe/Chisinau', b'Europe/Chisinau'), (b'Europe/Copenhagen', b'Europe/Copenhagen'), (b'Europe/Dublin', b'Europe/Dublin'), (b'Europe/Gibraltar', b'Europe/Gibraltar'), (b'Europe/Guernsey', b'Europe/Guernsey'), (b'Europe/Helsinki', b'Europe/Helsinki'), (b'Europe/Isle_of_Man', b'Europe/Isle_of_Man'), (b'Europe/Istanbul', b'Europe/Istanbul'), (b'Europe/Jersey', b'Europe/Jersey'), (b'Europe/Kaliningrad', b'Europe/Kaliningrad'), (b'Europe/Kiev', b'Europe/Kiev'), (b'Europe/Lisbon', b'Europe/Lisbon'), (b'Europe/Ljubljana', b'Europe/Ljubljana'), (b'Europe/London', b'Europe/London'), (b'Europe/Luxembourg', b'Europe/Luxembourg'), (b'Europe/Madrid', b'Europe/Madrid'), (b'Europe/Malta', b'Europe/Malta'), (b'Europe/Mariehamn', b'Europe/Mariehamn'), (b'Europe/Minsk', b'Europe/Minsk'), (b'Europe/Monaco', b'Europe/Monaco'), (b'Europe/Moscow', b'Europe/Moscow'), (b'Europe/Oslo', b'Europe/Oslo'), (b'Europe/Paris', b'Europe/Paris'), (b'Europe/Podgorica', b'Europe/Podgorica'), (b'Europe/Prague', b'Europe/Prague'), (b'Europe/Riga', b'Europe/Riga'), (b'Europe/Rome', b'Europe/Rome'), (b'Europe/Samara', b'Europe/Samara'), (b'Europe/San_Marino', b'Europe/San_Marino'), (b'Europe/Sarajevo', b'Europe/Sarajevo'), (b'Europe/Simferopol', b'Europe/Simferopol'), (b'Europe/Skopje', b'Europe/Skopje'), (b'Europe/Sofia', b'Europe/Sofia'), (b'Europe/Stockholm', b'Europe/Stockholm'), (b'Europe/Tallinn', b'Europe/Tallinn'), (b'Europe/Tirane', b'Europe/Tirane'), (b'Europe/Uzhgorod', b'Europe/Uzhgorod'), (b'Europe/Vaduz', b'Europe/Vaduz'), (b'Europe/Vatican', b'Europe/Vatican'), (b'Europe/Vienna', b'Europe/Vienna'), (b'Europe/Vilnius', b'Europe/Vilnius'), (b'Europe/Volgograd', b'Europe/Volgograd'), (b'Europe/Warsaw', b'Europe/Warsaw'), (b'Europe/Zagreb', b'Europe/Zagreb'), (b'Europe/Zaporozhye', b'Europe/Zaporozhye'), (b'Europe/Zurich', b'Europe/Zurich'), (b'GMT', b'GMT'), (b'Indian/Antananarivo', b'Indian/Antananarivo'), (b'Indian/Chagos', b'Indian/Chagos'), (b'Indian/Christmas', b'Indian/Christmas'), (b'Indian/Cocos', b'Indian/Cocos'), (b'Indian/Comoro', b'Indian/Comoro'), (b'Indian/Kerguelen', b'Indian/Kerguelen'), (b'Indian/Mahe', b'Indian/Mahe'), (b'Indian/Maldives', b'Indian/Maldives'), (b'Indian/Mauritius', b'Indian/Mauritius'), (b'Indian/Mayotte', b'Indian/Mayotte'), (b'Indian/Reunion', b'Indian/Reunion'), (b'Pacific/Apia', b'Pacific/Apia'), (b'Pacific/Auckland', b'Pacific/Auckland'), (b'Pacific/Bougainville', b'Pacific/Bougainville'), (b'Pacific/Chatham', b'Pacific/Chatham'), (b'Pacific/Chuuk', b'Pacific/Chuuk'), (b'Pacific/Easter', b'Pacific/Easter'), (b'Pacific/Efate', b'Pacific/Efate'), (b'Pacific/Enderbury', b'Pacific/Enderbury'), (b'Pacific/Fakaofo', b'Pacific/Fakaofo'), (b'Pacific/Fiji', b'Pacific/Fiji'), (b'Pacific/Funafuti', b'Pacific/Funafuti'), (b'Pacific/Galapagos', b'Pacific/Galapagos'), (b'Pacific/Gambier', b'Pacific/Gambier'), (b'Pacific/Guadalcanal', b'Pacific/Guadalcanal'), (b'Pacific/Guam', b'Pacific/Guam'), (b'Pacific/Honolulu', b'Pacific/Honolulu'), (b'Pacific/Johnston', b'Pacific/Johnston'), (b'Pacific/Kiritimati', b'Pacific/Kiritimati'), (b'Pacific/Kosrae', b'Pacific/Kosrae'), (b'Pacific/Kwajalein', b'Pacific/Kwajalein'), (b'Pacific/Majuro', b'Pacific/Majuro'), (b'Pacific/Marquesas', b'Pacific/Marquesas'), (b'Pacific/Midway', b'Pacific/Midway'), (b'Pacific/Nauru', b'Pacific/Nauru'), (b'Pacific/Niue', b'Pacific/Niue'), (b'Pacific/Norfolk', b'Pacific/Norfolk'), (b'Pacific/Noumea', b'Pacific/Noumea'), (b'Pacific/Pago_Pago', b'Pacific/Pago_Pago'), (b'Pacific/Palau', b'Pacific/Palau'), (b'Pacific/Pitcairn', b'Pacific/Pitcairn'), (b'Pacific/Pohnpei', b'Pacific/Pohnpei'), (b'Pacific/Port_Moresby', b'Pacific/Port_Moresby'), (b'Pacific/Rarotonga', b'Pacific/Rarotonga'), (b'Pacific/Saipan', b'Pacific/Saipan'), (b'Pacific/Tahiti', b'Pacific/Tahiti'), (b'Pacific/Tarawa', b'Pacific/Tarawa'), (b'Pacific/Tongatapu', b'Pacific/Tongatapu'), (b'Pacific/Wake', b'Pacific/Wake'), (b'Pacific/Wallis', b'Pacific/Wallis'), (b'US/Alaska', b'US/Alaska'), (b'US/Arizona', b'US/Arizona'), (b'US/Central', b'US/Central'), (b'US/Eastern', b'US/Eastern'), (b'US/Hawaii', b'US/Hawaii'), (b'US/Mountain', b'US/Mountain'), (b'US/Pacific', b'US/Pacific'), (b'UTC', b'UTC')])),
                ('scheduledatetimefield', models.CharField(max_length=128, verbose_name=b'Schedule Datetime', blank=True)),
                ('schedulegamefield', models.CharField(max_length=128, verbose_name=b'Schdule Game', blank=True)),
                ('schedulerunnersfield', models.CharField(max_length=128, verbose_name=b'Schedule Runners', blank=True)),
                ('scheduleestimatefield', models.CharField(max_length=128, verbose_name=b'Schedule Estimate', blank=True)),
                ('schedulesetupfield', models.CharField(max_length=128, verbose_name=b'Schedule Setup', blank=True)),
                ('schedulecommentatorsfield', models.CharField(max_length=128, verbose_name=b'Schedule Commentators', blank=True)),
                ('schedulecommentsfield', models.CharField(max_length=128, verbose_name=b'Schedule Comments', blank=True)),
                ('date', models.DateField()),
                ('locked', models.BooleanField(default=False, help_text=b'Requires special permission to edit this event or anything associated with it')),
                ('donationemailtemplate', models.ForeignKey(related_name='event_donation_templates', on_delete=django.db.models.deletion.PROTECT, default=None, blank=True, to='post_office.EmailTemplate', null=True, verbose_name=b'Donation Email Template')),
                ('pendingdonationemailtemplate', models.ForeignKey(related_name='event_pending_donation_templates', on_delete=django.db.models.deletion.PROTECT, default=None, blank=True, to='post_office.EmailTemplate', null=True, verbose_name=b'Pending Donation Email Template')),
            ],
            options={
                'ordering': ('date',),
                'get_latest_by': 'date',
                'permissions': (('can_edit_locked_events', 'Can edit locked events'),),
            },
        ),
        migrations.CreateModel(
            name='FlowModel',
            fields=[
                ('id', models.ForeignKey(primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL)),
                ('flow', oauth2client.django_orm.FlowField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Log',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name=b'Timestamp')),
                ('category', models.CharField(default=b'other', max_length=64, verbose_name=b'Category')),
                ('message', models.TextField(verbose_name=b'Message', blank=True)),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='tracker.Event', null=True)),
                ('user', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'ordering': ['-timestamp'],
                'verbose_name': 'Log',
                'permissions': (('can_view_log', 'Can view tracker logs'), ('can_change_log', 'Can change tracker logs')),
            },
        ),
        migrations.CreateModel(
            name='PostbackURL',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('url', models.URLField(verbose_name=b'URL')),
                ('event', models.ForeignKey(related_name='postbacks', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Event', to='tracker.Event')),
            ],
        ),
        migrations.CreateModel(
            name='Prize',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64)),
                ('image', models.URLField(max_length=1024, null=True, blank=True)),
                ('altimage', models.URLField(help_text=b'A second image to display in situations where the default image is not appropriate (tight spaces, stream, etc...)', max_length=1024, null=True, verbose_name=b'Alternate Image', blank=True)),
                ('imagefile', models.FileField(null=True, upload_to=b'prizes', blank=True)),
                ('description', models.TextField(max_length=1024, null=True, blank=True)),
                ('shortdescription', models.TextField(help_text=b'Alternative description text to display in tight spaces', max_length=256, verbose_name=b'Short Description', blank=True)),
                ('extrainfo', models.TextField(max_length=1024, null=True, blank=True)),
                ('estimatedvalue', models.DecimalField(decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero], max_digits=20, blank=True, null=True, verbose_name=b'Estimated Value')),
                ('minimumbid', models.DecimalField(default=Decimal('5.0'), verbose_name=b'Minimum Bid', max_digits=20, decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('maximumbid', models.DecimalField(decimal_places=2, default=Decimal('5.0'), validators=[tracker.validators.positive, tracker.validators.nonzero], max_digits=20, blank=True, null=True, verbose_name=b'Maximum Bid')),
                ('sumdonations', models.BooleanField(default=False, verbose_name=b'Sum Donations')),
                ('randomdraw', models.BooleanField(default=True, verbose_name=b'Random Draw')),
                ('ticketdraw', models.BooleanField(default=False, verbose_name=b'Ticket Draw')),
                ('starttime', models.DateTimeField(null=True, verbose_name=b'Start Time', blank=True)),
                ('endtime', models.DateTimeField(null=True, verbose_name=b'End Time', blank=True)),
                ('maxwinners', models.IntegerField(default=1, verbose_name=b'Max Winners', validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('maxmultiwin', models.IntegerField(default=1, verbose_name=b'Max Wins per Donor', validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('provided', models.CharField(max_length=64, null=True, verbose_name=b'Provided By', blank=True)),
                ('provideremail', models.EmailField(max_length=128, null=True, verbose_name=b'Provider Email', blank=True)),
                ('acceptemailsent', models.BooleanField(default=False, verbose_name=b'Accept/Deny Email Sent')),
                ('creator', models.CharField(max_length=64, null=True, verbose_name=b'Creator', blank=True)),
                ('creatoremail', models.EmailField(max_length=128, null=True, verbose_name=b'Creator Email', blank=True)),
                ('creatorwebsite', models.CharField(max_length=128, null=True, verbose_name=b'Creator Website', blank=True)),
                ('state', models.CharField(default=b'PENDING', max_length=32, choices=[(b'PENDING', b'Pending'), (b'ACCEPTED', b'Accepted'), (b'DENIED', b'Denied'), (b'FLAGGED', b'Flagged')])),
            ],
            options={
                'ordering': ['event__date', 'startrun__starttime', 'starttime', 'name'],
            },
        ),
        migrations.CreateModel(
            name='PrizeCategory',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=64)),
            ],
            options={
                'verbose_name': 'Prize Category',
                'verbose_name_plural': 'Prize Categories',
            },
        ),
        migrations.CreateModel(
            name='PrizeTicket',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('amount', models.DecimalField(max_digits=20, decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero])),
                ('donation', models.ForeignKey(related_name='tickets', on_delete=django.db.models.deletion.PROTECT, to='tracker.Donation')),
                ('prize', models.ForeignKey(related_name='tickets', on_delete=django.db.models.deletion.PROTECT, to='tracker.Prize')),
            ],
            options={
                'ordering': ['-donation__timereceived'],
                'verbose_name': 'Prize Ticket',
            },
        ),
        migrations.CreateModel(
            name='PrizeWinner',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('pendingcount', models.IntegerField(default=1, help_text=b'The number of pending wins this donor has on this prize.', verbose_name=b'Pending Count', validators=[tracker.validators.positive])),
                ('acceptcount', models.IntegerField(default=0, help_text=b'The number of copied this winner has won and accepted.', verbose_name=b'Accept Count', validators=[tracker.validators.positive])),
                ('declinecount', models.IntegerField(default=0, help_text=b'The number of declines this donor has put towards this prize. Set it to the max prize multi win amount to prevent this donor from being entered from future drawings.', verbose_name=b'Decline Count', validators=[tracker.validators.positive])),
                ('sumcount', models.IntegerField(default=1, help_text=b'The total number of prize instances associated with this winner', verbose_name=b'Sum Counts', editable=False, validators=[tracker.validators.positive])),
                ('emailsent', models.BooleanField(default=False, verbose_name=b'Notification Email Sent')),
                ('shippingemailsent', models.BooleanField(default=False, verbose_name=b'Shipping Email Sent')),
                ('trackingnumber', models.CharField(max_length=64, verbose_name=b'Tracking Number', blank=True)),
                ('shippingstate', models.CharField(default=b'PENDING', max_length=64, verbose_name=b'Shipping State', choices=[(b'PENDING', b'Pending'), (b'SHIPPED', b'Shipped')])),
                ('shippingcost', models.DecimalField(decimal_places=2, validators=[tracker.validators.positive, tracker.validators.nonzero], max_digits=20, blank=True, null=True, verbose_name=b'Shipping Cost')),
                ('prize', models.ForeignKey(to='tracker.Prize', on_delete=django.db.models.deletion.PROTECT)),
                ('winner', models.ForeignKey(to='tracker.Donor', on_delete=django.db.models.deletion.PROTECT)),
            ],
            options={
                'verbose_name': 'Prize Winner',
            },
        ),
        migrations.CreateModel(
            name='SpeedRun',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=64, editable=False)),
                ('deprecated_runners', models.CharField(max_length=1024, verbose_name=b'*DEPRECATED* Runners', blank=True)),
                ('description', models.TextField(max_length=1024, blank=True)),
                ('starttime', models.DateTimeField(verbose_name=b'Start Time')),
                ('endtime', models.DateTimeField(verbose_name=b'End Time')),
                ('event', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, default=tracker.models.event.LatestEvent, to='tracker.Event')),
                ('runners', models.ManyToManyField(to='tracker.Donor', null=True, blank=True)),
            ],
            options={
                'ordering': ['event__date', 'starttime'],
                'verbose_name': 'Speed Run',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('prepend', models.CharField(max_length=64, verbose_name=b'Template Prepend', blank=True)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, unique=True)),
            ],
            options={
                'verbose_name': 'User Profile',
                'permissions': (('show_rendertime', 'Can view page render times'), ('show_queries', 'Can view database queries'), ('sync_schedule', 'Can sync the schedule'), ('can_search', 'Can use search url')),
            },
        ),
        migrations.AddField(
            model_name='prize',
            name='category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='tracker.PrizeCategory', null=True),
        ),
        migrations.AddField(
            model_name='prize',
            name='endrun',
            field=models.ForeignKey(related_name='prize_end', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'End Run', blank=True, to='tracker.SpeedRun', null=True),
        ),
        migrations.AddField(
            model_name='prize',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, default=tracker.models.event.LatestEvent, to='tracker.Event'),
        ),
        migrations.AddField(
            model_name='prize',
            name='startrun',
            field=models.ForeignKey(related_name='prize_start', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Start Run', blank=True, to='tracker.SpeedRun', null=True),
        ),
        migrations.AddField(
            model_name='donorprizeentry',
            name='prize',
            field=models.ForeignKey(to='tracker.Prize', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='donorcache',
            name='event',
            field=models.ForeignKey(blank=True, to='tracker.Event', null=True),
        ),
        migrations.AddField(
            model_name='donation',
            name='donor',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, blank=True, to='tracker.Donor', null=True),
        ),
        migrations.AddField(
            model_name='donation',
            name='event',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, default=tracker.models.event.LatestEvent, to='tracker.Event'),
        ),
        migrations.AddField(
            model_name='bid',
            name='event',
            field=models.ForeignKey(related_name='bids', on_delete=django.db.models.deletion.PROTECT, blank=True, to='tracker.Event', help_text=b'Required for top level bids if Run is not set', null=True, verbose_name=b'Event'),
        ),
        migrations.AddField(
            model_name='bid',
            name='parent',
            field=mptt.fields.TreeForeignKey(related_name='options', on_delete=django.db.models.deletion.PROTECT, blank=True, editable=False, to='tracker.Bid', null=True, verbose_name=b'Parent'),
        ),
        migrations.AddField(
            model_name='bid',
            name='speedrun',
            field=models.ForeignKey(related_name='bids', on_delete=django.db.models.deletion.PROTECT, verbose_name=b'Run', blank=True, to='tracker.SpeedRun', null=True),
        ),
        migrations.AlterUniqueTogether(
            name='speedrun',
            unique_together=set([('name', 'event')]),
        ),
        migrations.AlterUniqueTogether(
            name='prizewinner',
            unique_together=set([('prize', 'winner')]),
        ),
        migrations.AlterUniqueTogether(
            name='prizeticket',
            unique_together=set([('prize', 'donation')]),
        ),
        migrations.AlterUniqueTogether(
            name='prize',
            unique_together=set([('name', 'event')]),
        ),
        migrations.AlterUniqueTogether(
            name='donorprizeentry',
            unique_together=set([('prize', 'donor')]),
        ),
        migrations.AlterUniqueTogether(
            name='donorcache',
            unique_together=set([('event', 'donor')]),
        ),
        migrations.AlterUniqueTogether(
            name='donationbid',
            unique_together=set([('bid', 'donation')]),
        ),
        migrations.AlterUniqueTogether(
            name='bid',
            unique_together=set([('event', 'name', 'speedrun', 'parent')]),
        ),
    ]
