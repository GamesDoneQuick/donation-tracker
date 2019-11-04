# -*- coding: utf-8 -*-


from django.db import migrations, models
import tracker.validators
import tracker.models.donation
import mptt.fields
from decimal import Decimal
import tracker.models.prize
import django.utils.timezone
from django.conf import settings
import django

if django.VERSION < (1, 10, 0):
    import oauth2client.django_orm
else:
    # removed because of django 1.10 compatibility
    # noinspection PyPep8Naming
    class oauth2client:
        # noinspection PyPep8Naming
        class django_orm:
            def __init__(self):
                pass

            class CredentialsField(models.Field):
                def __init__(self, *args, **kwargs):
                    super(oauth2client.django_orm.CredentialsField, self).__init__(
                        *args, **kwargs
                    )
                    pass

            class FlowField(models.Field):
                def __init__(self, *args, **kwargs):
                    super(oauth2client.django_orm.FlowField, self).__init__(
                        *args, **kwargs
                    )
                    pass

        def __init__(self):
            pass

    pass


class Migration(migrations.Migration):

    dependencies = [
        ("post_office", "__first__"),
        ("auth", "0006_require_contenttypes_0002"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Bid",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=64)),
                (
                    "state",
                    models.CharField(
                        default="OPENED",
                        max_length=32,
                        choices=[
                            ("PENDING", "Pending"),
                            ("DENIED", "Denied"),
                            ("HIDDEN", "Hidden"),
                            ("OPENED", "Opened"),
                            ("CLOSED", "Closed"),
                        ],
                    ),
                ),
                ("description", models.TextField(max_length=1024, blank=True)),
                (
                    "shortdescription",
                    models.TextField(
                        help_text="Alternative description text to display in tight spaces",
                        max_length=256,
                        verbose_name="Short Description",
                        blank=True,
                    ),
                ),
                (
                    "goal",
                    models.DecimalField(
                        default=None,
                        null=True,
                        max_digits=20,
                        decimal_places=2,
                        blank=True,
                    ),
                ),
                (
                    "istarget",
                    models.BooleanField(
                        default=False,
                        help_text=b"Set this if this bid is a 'target' for donations (bottom level choice or challenge)",
                        verbose_name="Target",
                    ),
                ),
                (
                    "allowuseroptions",
                    models.BooleanField(
                        default=False,
                        help_text="If set, this will allow donors to specify their own options on the donate page (pending moderator approval)",
                        verbose_name="Allow User Options",
                    ),
                ),
                (
                    "revealedtime",
                    models.DateTimeField(
                        null=True, verbose_name="Revealed Time", blank=True
                    ),
                ),
                (
                    "total",
                    models.DecimalField(
                        default=Decimal("0.00"),
                        editable=False,
                        max_digits=20,
                        decimal_places=2,
                    ),
                ),
                ("count", models.IntegerField(editable=False)),
                ("lft", models.PositiveIntegerField(editable=False, db_index=True)),
                ("rght", models.PositiveIntegerField(editable=False, db_index=True)),
                ("tree_id", models.PositiveIntegerField(editable=False, db_index=True)),
                ("level", models.PositiveIntegerField(editable=False, db_index=True)),
                (
                    "biddependency",
                    models.ForeignKey(
                        related_name="depedent_bids",
                        on_delete=django.db.models.deletion.PROTECT,
                        verbose_name="Dependency",
                        blank=True,
                        to="tracker.Bid",
                        null=True,
                    ),
                ),
            ],
            options={
                "ordering": [
                    "event__date",
                    "speedrun__starttime",
                    "parent__name",
                    "name",
                ],
                "permissions": (
                    ("top_level_bid", "Can create new top level bids"),
                    ("delete_all_bids", "Can delete bids with donations attached"),
                    ("view_hidden", "Can view hidden bids"),
                ),
            },
        ),
        migrations.CreateModel(
            name="BidSuggestion",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=64, verbose_name="Name")),
                (
                    "bid",
                    models.ForeignKey(
                        related_name="suggestions",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="tracker.Bid",
                    ),
                ),
            ],
            options={"ordering": ["name"],},
        ),
        migrations.CreateModel(
            name="CredentialsModel",
            fields=[
                (
                    "id",
                    models.ForeignKey(
                        primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL
                    ),
                ),
                ("credentials", oauth2client.django_orm.CredentialsField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Donation",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "domain",
                    models.CharField(
                        default="LOCAL",
                        max_length=255,
                        choices=[
                            ("LOCAL", "Local"),
                            ("CHIPIN", "ChipIn"),
                            ("PAYPAL", "PayPal"),
                        ],
                    ),
                ),
                (
                    "domainId",
                    models.CharField(
                        unique=True, max_length=160, editable=False, blank=True
                    ),
                ),
                (
                    "transactionstate",
                    models.CharField(
                        default="PENDING",
                        max_length=64,
                        verbose_name="Transaction State",
                        choices=[
                            ("PENDING", "Pending"),
                            ("COMPLETED", "Completed"),
                            ("CANCELLED", "Cancelled"),
                            ("FLAGGED", "Flagged"),
                        ],
                    ),
                ),
                (
                    "bidstate",
                    models.CharField(
                        default="PENDING",
                        max_length=255,
                        verbose_name="Bid State",
                        choices=[
                            ("PENDING", "Pending"),
                            ("IGNORED", "Ignored"),
                            ("PROCESSED", "Processed"),
                            ("FLAGGED", "Flagged"),
                        ],
                    ),
                ),
                (
                    "readstate",
                    models.CharField(
                        default="PENDING",
                        max_length=255,
                        verbose_name="Read State",
                        choices=[
                            ("PENDING", "Pending"),
                            ("READY", "Ready to Read"),
                            ("IGNORED", "Ignored"),
                            ("READ", "Read"),
                            ("FLAGGED", "Flagged"),
                        ],
                    ),
                ),
                (
                    "commentstate",
                    models.CharField(
                        default="ABSENT",
                        max_length=255,
                        verbose_name="Comment State",
                        choices=[
                            ("ABSENT", "Absent"),
                            ("PENDING", "Pending"),
                            ("DENIED", "Denied"),
                            ("APPROVED", "Approved"),
                            ("FLAGGED", "Flagged"),
                        ],
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        default=Decimal("0.00"),
                        verbose_name="Donation Amount",
                        max_digits=20,
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "fee",
                    models.DecimalField(
                        default=Decimal("0.00"),
                        verbose_name="Donation Fee",
                        max_digits=20,
                        decimal_places=2,
                        validators=[tracker.validators.positive],
                    ),
                ),
                (
                    "currency",
                    models.CharField(
                        max_length=8,
                        verbose_name="Currency",
                        choices=[("USD", "US Dollars"), ("CAD", "Canadian Dollars")],
                    ),
                ),
                (
                    "timereceived",
                    models.DateTimeField(
                        default=django.utils.timezone.now, verbose_name="Time Received"
                    ),
                ),
                ("comment", models.TextField(verbose_name="Comment", blank=True)),
                (
                    "modcomment",
                    models.TextField(verbose_name="Moderator Comment", blank=True),
                ),
                ("testdonation", models.BooleanField(default=False)),
                (
                    "requestedvisibility",
                    models.CharField(
                        default="CURR",
                        max_length=32,
                        verbose_name="Requested Visibility",
                        choices=[
                            ("CURR", "Use Existing (Anonymous if not set)"),
                            ("FULL", "Fully Visible"),
                            ("FIRST", "First Name, Last Initial"),
                            ("ALIAS", "Alias Only"),
                            ("ANON", "Anonymous"),
                        ],
                    ),
                ),
                (
                    "requestedalias",
                    models.CharField(
                        max_length=32,
                        null=True,
                        verbose_name="Requested Alias",
                        blank=True,
                    ),
                ),
                (
                    "requestedemail",
                    models.EmailField(
                        max_length=128,
                        null=True,
                        verbose_name="Requested Contact Email",
                        blank=True,
                    ),
                ),
                (
                    "commentlanguage",
                    models.CharField(
                        default="un",
                        max_length=32,
                        verbose_name="Comment Language",
                        choices=[
                            ("un", "Unknown"),
                            ("en", "English"),
                            ("fr", "French"),
                            ("de", "German"),
                        ],
                    ),
                ),
            ],
            options={
                "ordering": ["-timereceived"],
                "get_latest_by": "timereceived",
                "permissions": (
                    ("delete_all_donations", "Can delete non-local donations"),
                    ("view_full_list", "Can view full donation list"),
                    ("view_comments", "Can view all comments"),
                    ("view_pending", "Can view pending donations"),
                    ("view_test", "Can view test donations"),
                    ("send_to_reader", "Can send donations to the reader"),
                ),
            },
        ),
        migrations.CreateModel(
            name="DonationBid",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        max_digits=20,
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "bid",
                    models.ForeignKey(
                        related_name="bids",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="tracker.Bid",
                    ),
                ),
                (
                    "donation",
                    models.ForeignKey(
                        related_name="bids",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="tracker.Donation",
                    ),
                ),
            ],
            options={
                "ordering": ["-donation__timereceived"],
                "verbose_name": "Donation Bid",
            },
        ),
        migrations.CreateModel(
            name="Donor",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "email",
                    models.EmailField(max_length=128, verbose_name="Contact Email"),
                ),
                ("alias", models.CharField(max_length=32, null=True, blank=True)),
                (
                    "firstname",
                    models.CharField(
                        max_length=64, verbose_name="First Name", blank=True
                    ),
                ),
                (
                    "lastname",
                    models.CharField(
                        max_length=64, verbose_name="Last Name", blank=True
                    ),
                ),
                (
                    "visibility",
                    models.CharField(
                        default="FIRST",
                        max_length=32,
                        choices=[
                            ("FULL", "Fully Visible"),
                            ("FIRST", "First Name, Last Initial"),
                            ("ALIAS", "Alias Only"),
                            ("ANON", "Anonymous"),
                        ],
                    ),
                ),
                (
                    "addresscity",
                    models.CharField(max_length=128, verbose_name="City", blank=True),
                ),
                (
                    "addressstreet",
                    models.CharField(
                        max_length=128, verbose_name="Street/P.O. Box", blank=True
                    ),
                ),
                (
                    "addressstate",
                    models.CharField(
                        max_length=128, verbose_name="State/Province", blank=True
                    ),
                ),
                (
                    "addresszip",
                    models.CharField(
                        max_length=128, verbose_name="Zip/Postal Code", blank=True
                    ),
                ),
                (
                    "addresscountry",
                    models.CharField(
                        max_length=128, verbose_name="Country", blank=True
                    ),
                ),
                (
                    "paypalemail",
                    models.EmailField(
                        max_length=128,
                        unique=True,
                        null=True,
                        verbose_name="Paypal Email",
                        blank=True,
                    ),
                ),
                (
                    "runneryoutube",
                    models.CharField(
                        max_length=128,
                        unique=True,
                        null=True,
                        verbose_name="Youtube Account",
                        blank=True,
                    ),
                ),
                (
                    "runnertwitch",
                    models.CharField(
                        max_length=128,
                        unique=True,
                        null=True,
                        verbose_name="Twitch Account",
                        blank=True,
                    ),
                ),
                (
                    "runnertwitter",
                    models.CharField(
                        max_length=128,
                        unique=True,
                        null=True,
                        verbose_name="Twitter Account",
                        blank=True,
                    ),
                ),
            ],
            options={
                "ordering": ["lastname", "firstname", "email"],
                "permissions": (
                    ("delete_all_donors", "Can delete donors with cleared donations"),
                    ("view_usernames", "Can view full usernames"),
                    ("view_emails", "Can view email addresses"),
                ),
            },
        ),
        migrations.CreateModel(
            name="DonorCache",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "donation_total",
                    models.DecimalField(
                        default=0,
                        editable=False,
                        max_digits=20,
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "donation_count",
                    models.IntegerField(
                        default=0,
                        editable=False,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "donation_avg",
                    models.DecimalField(
                        default=0,
                        editable=False,
                        max_digits=20,
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "donation_max",
                    models.DecimalField(
                        default=0,
                        editable=False,
                        max_digits=20,
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                ("donor", models.ForeignKey(to="tracker.Donor")),
            ],
            options={"ordering": ("donor",),},
        ),
        migrations.CreateModel(
            name="DonorPrizeEntry",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "weight",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("1.0"),
                        max_digits=20,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                        help_text="This is the weight to apply this entry in the drawing (if weight is applicable).",
                        verbose_name="Entry Weight",
                    ),
                ),
                (
                    "donor",
                    models.ForeignKey(
                        to="tracker.Donor", on_delete=django.db.models.deletion.PROTECT
                    ),
                ),
            ],
            options={
                "verbose_name": "Donor Prize Entry",
                "verbose_name_plural": "Donor Prize Entries",
            },
        ),
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("short", models.CharField(unique=True, max_length=64)),
                ("name", models.CharField(max_length=128)),
                (
                    "receivername",
                    models.CharField(
                        max_length=128, verbose_name="Receiver Name", blank=True
                    ),
                ),
                (
                    "targetamount",
                    models.DecimalField(
                        verbose_name="Target Amount",
                        max_digits=20,
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "usepaypalsandbox",
                    models.BooleanField(
                        default=False, verbose_name="Use Paypal Sandbox"
                    ),
                ),
                (
                    "paypalemail",
                    models.EmailField(max_length=128, verbose_name="Receiver Paypal"),
                ),
                (
                    "paypalcurrency",
                    models.CharField(
                        default="USD",
                        max_length=8,
                        verbose_name="Currency",
                        choices=[("USD", "US Dollars"), ("CAD", "Canadian Dollars")],
                    ),
                ),
                (
                    "donationemailsender",
                    models.EmailField(
                        max_length=128,
                        null=True,
                        verbose_name="Donation Email Sender",
                        blank=True,
                    ),
                ),
                (
                    "scheduleid",
                    models.CharField(
                        max_length=128,
                        unique=True,
                        null=True,
                        verbose_name="Schedule ID",
                        blank=True,
                    ),
                ),
                (
                    "scheduletimezone",
                    models.CharField(
                        default="US/Eastern",
                        max_length=64,
                        verbose_name="Schedule Timezone",
                        blank=True,
                        choices=[
                            ("Africa/Abidjan", "Africa/Abidjan"),
                            ("Africa/Accra", "Africa/Accra"),
                            ("Africa/Addis_Ababa", "Africa/Addis_Ababa"),
                            ("Africa/Algiers", "Africa/Algiers"),
                            ("Africa/Asmara", "Africa/Asmara"),
                            ("Africa/Bamako", "Africa/Bamako"),
                            ("Africa/Bangui", "Africa/Bangui"),
                            ("Africa/Banjul", "Africa/Banjul"),
                            ("Africa/Bissau", "Africa/Bissau"),
                            ("Africa/Blantyre", "Africa/Blantyre"),
                            ("Africa/Brazzaville", "Africa/Brazzaville"),
                            ("Africa/Bujumbura", "Africa/Bujumbura"),
                            ("Africa/Cairo", "Africa/Cairo"),
                            ("Africa/Casablanca", "Africa/Casablanca"),
                            ("Africa/Ceuta", "Africa/Ceuta"),
                            ("Africa/Conakry", "Africa/Conakry"),
                            ("Africa/Dakar", "Africa/Dakar"),
                            ("Africa/Dar_es_Salaam", "Africa/Dar_es_Salaam"),
                            ("Africa/Djibouti", "Africa/Djibouti"),
                            ("Africa/Douala", "Africa/Douala"),
                            ("Africa/El_Aaiun", "Africa/El_Aaiun"),
                            ("Africa/Freetown", "Africa/Freetown"),
                            ("Africa/Gaborone", "Africa/Gaborone"),
                            ("Africa/Harare", "Africa/Harare"),
                            ("Africa/Johannesburg", "Africa/Johannesburg"),
                            ("Africa/Juba", "Africa/Juba"),
                            ("Africa/Kampala", "Africa/Kampala"),
                            ("Africa/Khartoum", "Africa/Khartoum"),
                            ("Africa/Kigali", "Africa/Kigali"),
                            ("Africa/Kinshasa", "Africa/Kinshasa"),
                            ("Africa/Lagos", "Africa/Lagos"),
                            ("Africa/Libreville", "Africa/Libreville"),
                            ("Africa/Lome", "Africa/Lome"),
                            ("Africa/Luanda", "Africa/Luanda"),
                            ("Africa/Lubumbashi", "Africa/Lubumbashi"),
                            ("Africa/Lusaka", "Africa/Lusaka"),
                            ("Africa/Malabo", "Africa/Malabo"),
                            ("Africa/Maputo", "Africa/Maputo"),
                            ("Africa/Maseru", "Africa/Maseru"),
                            ("Africa/Mbabane", "Africa/Mbabane"),
                            ("Africa/Mogadishu", "Africa/Mogadishu"),
                            ("Africa/Monrovia", "Africa/Monrovia"),
                            ("Africa/Nairobi", "Africa/Nairobi"),
                            ("Africa/Ndjamena", "Africa/Ndjamena"),
                            ("Africa/Niamey", "Africa/Niamey"),
                            ("Africa/Nouakchott", "Africa/Nouakchott"),
                            ("Africa/Ouagadougou", "Africa/Ouagadougou"),
                            ("Africa/Porto-Novo", "Africa/Porto-Novo"),
                            ("Africa/Sao_Tome", "Africa/Sao_Tome"),
                            ("Africa/Tripoli", "Africa/Tripoli"),
                            ("Africa/Tunis", "Africa/Tunis"),
                            ("Africa/Windhoek", "Africa/Windhoek"),
                            ("America/Adak", "America/Adak"),
                            ("America/Anchorage", "America/Anchorage"),
                            ("America/Anguilla", "America/Anguilla"),
                            ("America/Antigua", "America/Antigua"),
                            ("America/Araguaina", "America/Araguaina"),
                            (
                                "America/Argentina/Buenos_Aires",
                                "America/Argentina/Buenos_Aires",
                            ),
                            (
                                "America/Argentina/Catamarca",
                                "America/Argentina/Catamarca",
                            ),
                            ("America/Argentina/Cordoba", "America/Argentina/Cordoba"),
                            ("America/Argentina/Jujuy", "America/Argentina/Jujuy"),
                            (
                                "America/Argentina/La_Rioja",
                                "America/Argentina/La_Rioja",
                            ),
                            ("America/Argentina/Mendoza", "America/Argentina/Mendoza"),
                            (
                                "America/Argentina/Rio_Gallegos",
                                "America/Argentina/Rio_Gallegos",
                            ),
                            ("America/Argentina/Salta", "America/Argentina/Salta"),
                            (
                                "America/Argentina/San_Juan",
                                "America/Argentina/San_Juan",
                            ),
                            (
                                "America/Argentina/San_Luis",
                                "America/Argentina/San_Luis",
                            ),
                            ("America/Argentina/Tucuman", "America/Argentina/Tucuman"),
                            ("America/Argentina/Ushuaia", "America/Argentina/Ushuaia"),
                            ("America/Aruba", "America/Aruba"),
                            ("America/Asuncion", "America/Asuncion"),
                            ("America/Atikokan", "America/Atikokan"),
                            ("America/Bahia", "America/Bahia"),
                            ("America/Bahia_Banderas", "America/Bahia_Banderas"),
                            ("America/Barbados", "America/Barbados"),
                            ("America/Belem", "America/Belem"),
                            ("America/Belize", "America/Belize"),
                            ("America/Blanc-Sablon", "America/Blanc-Sablon"),
                            ("America/Boa_Vista", "America/Boa_Vista"),
                            ("America/Bogota", "America/Bogota"),
                            ("America/Boise", "America/Boise"),
                            ("America/Cambridge_Bay", "America/Cambridge_Bay"),
                            ("America/Campo_Grande", "America/Campo_Grande"),
                            ("America/Cancun", "America/Cancun"),
                            ("America/Caracas", "America/Caracas"),
                            ("America/Cayenne", "America/Cayenne"),
                            ("America/Cayman", "America/Cayman"),
                            ("America/Chicago", "America/Chicago"),
                            ("America/Chihuahua", "America/Chihuahua"),
                            ("America/Costa_Rica", "America/Costa_Rica"),
                            ("America/Creston", "America/Creston"),
                            ("America/Cuiaba", "America/Cuiaba"),
                            ("America/Curacao", "America/Curacao"),
                            ("America/Danmarkshavn", "America/Danmarkshavn"),
                            ("America/Dawson", "America/Dawson"),
                            ("America/Dawson_Creek", "America/Dawson_Creek"),
                            ("America/Denver", "America/Denver"),
                            ("America/Detroit", "America/Detroit"),
                            ("America/Dominica", "America/Dominica"),
                            ("America/Edmonton", "America/Edmonton"),
                            ("America/Eirunepe", "America/Eirunepe"),
                            ("America/El_Salvador", "America/El_Salvador"),
                            ("America/Fortaleza", "America/Fortaleza"),
                            ("America/Glace_Bay", "America/Glace_Bay"),
                            ("America/Godthab", "America/Godthab"),
                            ("America/Goose_Bay", "America/Goose_Bay"),
                            ("America/Grand_Turk", "America/Grand_Turk"),
                            ("America/Grenada", "America/Grenada"),
                            ("America/Guadeloupe", "America/Guadeloupe"),
                            ("America/Guatemala", "America/Guatemala"),
                            ("America/Guayaquil", "America/Guayaquil"),
                            ("America/Guyana", "America/Guyana"),
                            ("America/Halifax", "America/Halifax"),
                            ("America/Havana", "America/Havana"),
                            ("America/Hermosillo", "America/Hermosillo"),
                            (
                                "America/Indiana/Indianapolis",
                                "America/Indiana/Indianapolis",
                            ),
                            ("America/Indiana/Knox", "America/Indiana/Knox"),
                            ("America/Indiana/Marengo", "America/Indiana/Marengo"),
                            (
                                "America/Indiana/Petersburg",
                                "America/Indiana/Petersburg",
                            ),
                            ("America/Indiana/Tell_City", "America/Indiana/Tell_City"),
                            ("America/Indiana/Vevay", "America/Indiana/Vevay"),
                            ("America/Indiana/Vincennes", "America/Indiana/Vincennes"),
                            ("America/Indiana/Winamac", "America/Indiana/Winamac"),
                            ("America/Inuvik", "America/Inuvik"),
                            ("America/Iqaluit", "America/Iqaluit"),
                            ("America/Jamaica", "America/Jamaica"),
                            ("America/Juneau", "America/Juneau"),
                            (
                                "America/Kentucky/Louisville",
                                "America/Kentucky/Louisville",
                            ),
                            (
                                "America/Kentucky/Monticello",
                                "America/Kentucky/Monticello",
                            ),
                            ("America/Kralendijk", "America/Kralendijk"),
                            ("America/La_Paz", "America/La_Paz"),
                            ("America/Lima", "America/Lima"),
                            ("America/Los_Angeles", "America/Los_Angeles"),
                            ("America/Lower_Princes", "America/Lower_Princes"),
                            ("America/Maceio", "America/Maceio"),
                            ("America/Managua", "America/Managua"),
                            ("America/Manaus", "America/Manaus"),
                            ("America/Marigot", "America/Marigot"),
                            ("America/Martinique", "America/Martinique"),
                            ("America/Matamoros", "America/Matamoros"),
                            ("America/Mazatlan", "America/Mazatlan"),
                            ("America/Menominee", "America/Menominee"),
                            ("America/Merida", "America/Merida"),
                            ("America/Metlakatla", "America/Metlakatla"),
                            ("America/Mexico_City", "America/Mexico_City"),
                            ("America/Miquelon", "America/Miquelon"),
                            ("America/Moncton", "America/Moncton"),
                            ("America/Monterrey", "America/Monterrey"),
                            ("America/Montevideo", "America/Montevideo"),
                            ("America/Montserrat", "America/Montserrat"),
                            ("America/Nassau", "America/Nassau"),
                            ("America/New_York", "America/New_York"),
                            ("America/Nipigon", "America/Nipigon"),
                            ("America/Nome", "America/Nome"),
                            ("America/Noronha", "America/Noronha"),
                            (
                                "America/North_Dakota/Beulah",
                                "America/North_Dakota/Beulah",
                            ),
                            (
                                "America/North_Dakota/Center",
                                "America/North_Dakota/Center",
                            ),
                            (
                                "America/North_Dakota/New_Salem",
                                "America/North_Dakota/New_Salem",
                            ),
                            ("America/Ojinaga", "America/Ojinaga"),
                            ("America/Panama", "America/Panama"),
                            ("America/Pangnirtung", "America/Pangnirtung"),
                            ("America/Paramaribo", "America/Paramaribo"),
                            ("America/Phoenix", "America/Phoenix"),
                            ("America/Port-au-Prince", "America/Port-au-Prince"),
                            ("America/Port_of_Spain", "America/Port_of_Spain"),
                            ("America/Porto_Velho", "America/Porto_Velho"),
                            ("America/Puerto_Rico", "America/Puerto_Rico"),
                            ("America/Rainy_River", "America/Rainy_River"),
                            ("America/Rankin_Inlet", "America/Rankin_Inlet"),
                            ("America/Recife", "America/Recife"),
                            ("America/Regina", "America/Regina"),
                            ("America/Resolute", "America/Resolute"),
                            ("America/Rio_Branco", "America/Rio_Branco"),
                            ("America/Santa_Isabel", "America/Santa_Isabel"),
                            ("America/Santarem", "America/Santarem"),
                            ("America/Santiago", "America/Santiago"),
                            ("America/Santo_Domingo", "America/Santo_Domingo"),
                            ("America/Sao_Paulo", "America/Sao_Paulo"),
                            ("America/Scoresbysund", "America/Scoresbysund"),
                            ("America/Sitka", "America/Sitka"),
                            ("America/St_Barthelemy", "America/St_Barthelemy"),
                            ("America/St_Johns", "America/St_Johns"),
                            ("America/St_Kitts", "America/St_Kitts"),
                            ("America/St_Lucia", "America/St_Lucia"),
                            ("America/St_Thomas", "America/St_Thomas"),
                            ("America/St_Vincent", "America/St_Vincent"),
                            ("America/Swift_Current", "America/Swift_Current"),
                            ("America/Tegucigalpa", "America/Tegucigalpa"),
                            ("America/Thule", "America/Thule"),
                            ("America/Thunder_Bay", "America/Thunder_Bay"),
                            ("America/Tijuana", "America/Tijuana"),
                            ("America/Toronto", "America/Toronto"),
                            ("America/Tortola", "America/Tortola"),
                            ("America/Vancouver", "America/Vancouver"),
                            ("America/Whitehorse", "America/Whitehorse"),
                            ("America/Winnipeg", "America/Winnipeg"),
                            ("America/Yakutat", "America/Yakutat"),
                            ("America/Yellowknife", "America/Yellowknife"),
                            ("Antarctica/Casey", "Antarctica/Casey"),
                            ("Antarctica/Davis", "Antarctica/Davis"),
                            ("Antarctica/DumontDUrville", "Antarctica/DumontDUrville"),
                            ("Antarctica/Macquarie", "Antarctica/Macquarie"),
                            ("Antarctica/Mawson", "Antarctica/Mawson"),
                            ("Antarctica/McMurdo", "Antarctica/McMurdo"),
                            ("Antarctica/Palmer", "Antarctica/Palmer"),
                            ("Antarctica/Rothera", "Antarctica/Rothera"),
                            ("Antarctica/Syowa", "Antarctica/Syowa"),
                            ("Antarctica/Troll", "Antarctica/Troll"),
                            ("Antarctica/Vostok", "Antarctica/Vostok"),
                            ("Arctic/Longyearbyen", "Arctic/Longyearbyen"),
                            ("Asia/Aden", "Asia/Aden"),
                            ("Asia/Almaty", "Asia/Almaty"),
                            ("Asia/Amman", "Asia/Amman"),
                            ("Asia/Anadyr", "Asia/Anadyr"),
                            ("Asia/Aqtau", "Asia/Aqtau"),
                            ("Asia/Aqtobe", "Asia/Aqtobe"),
                            ("Asia/Ashgabat", "Asia/Ashgabat"),
                            ("Asia/Baghdad", "Asia/Baghdad"),
                            ("Asia/Bahrain", "Asia/Bahrain"),
                            ("Asia/Baku", "Asia/Baku"),
                            ("Asia/Bangkok", "Asia/Bangkok"),
                            ("Asia/Beirut", "Asia/Beirut"),
                            ("Asia/Bishkek", "Asia/Bishkek"),
                            ("Asia/Brunei", "Asia/Brunei"),
                            ("Asia/Chita", "Asia/Chita"),
                            ("Asia/Choibalsan", "Asia/Choibalsan"),
                            ("Asia/Colombo", "Asia/Colombo"),
                            ("Asia/Damascus", "Asia/Damascus"),
                            ("Asia/Dhaka", "Asia/Dhaka"),
                            ("Asia/Dili", "Asia/Dili"),
                            ("Asia/Dubai", "Asia/Dubai"),
                            ("Asia/Dushanbe", "Asia/Dushanbe"),
                            ("Asia/Gaza", "Asia/Gaza"),
                            ("Asia/Hebron", "Asia/Hebron"),
                            ("Asia/Ho_Chi_Minh", "Asia/Ho_Chi_Minh"),
                            ("Asia/Hong_Kong", "Asia/Hong_Kong"),
                            ("Asia/Hovd", "Asia/Hovd"),
                            ("Asia/Irkutsk", "Asia/Irkutsk"),
                            ("Asia/Jakarta", "Asia/Jakarta"),
                            ("Asia/Jayapura", "Asia/Jayapura"),
                            ("Asia/Jerusalem", "Asia/Jerusalem"),
                            ("Asia/Kabul", "Asia/Kabul"),
                            ("Asia/Kamchatka", "Asia/Kamchatka"),
                            ("Asia/Karachi", "Asia/Karachi"),
                            ("Asia/Kathmandu", "Asia/Kathmandu"),
                            ("Asia/Khandyga", "Asia/Khandyga"),
                            ("Asia/Kolkata", "Asia/Kolkata"),
                            ("Asia/Krasnoyarsk", "Asia/Krasnoyarsk"),
                            ("Asia/Kuala_Lumpur", "Asia/Kuala_Lumpur"),
                            ("Asia/Kuching", "Asia/Kuching"),
                            ("Asia/Kuwait", "Asia/Kuwait"),
                            ("Asia/Macau", "Asia/Macau"),
                            ("Asia/Magadan", "Asia/Magadan"),
                            ("Asia/Makassar", "Asia/Makassar"),
                            ("Asia/Manila", "Asia/Manila"),
                            ("Asia/Muscat", "Asia/Muscat"),
                            ("Asia/Nicosia", "Asia/Nicosia"),
                            ("Asia/Novokuznetsk", "Asia/Novokuznetsk"),
                            ("Asia/Novosibirsk", "Asia/Novosibirsk"),
                            ("Asia/Omsk", "Asia/Omsk"),
                            ("Asia/Oral", "Asia/Oral"),
                            ("Asia/Phnom_Penh", "Asia/Phnom_Penh"),
                            ("Asia/Pontianak", "Asia/Pontianak"),
                            ("Asia/Pyongyang", "Asia/Pyongyang"),
                            ("Asia/Qatar", "Asia/Qatar"),
                            ("Asia/Qyzylorda", "Asia/Qyzylorda"),
                            ("Asia/Rangoon", "Asia/Rangoon"),
                            ("Asia/Riyadh", "Asia/Riyadh"),
                            ("Asia/Sakhalin", "Asia/Sakhalin"),
                            ("Asia/Samarkand", "Asia/Samarkand"),
                            ("Asia/Seoul", "Asia/Seoul"),
                            ("Asia/Shanghai", "Asia/Shanghai"),
                            ("Asia/Singapore", "Asia/Singapore"),
                            ("Asia/Srednekolymsk", "Asia/Srednekolymsk"),
                            ("Asia/Taipei", "Asia/Taipei"),
                            ("Asia/Tashkent", "Asia/Tashkent"),
                            ("Asia/Tbilisi", "Asia/Tbilisi"),
                            ("Asia/Tehran", "Asia/Tehran"),
                            ("Asia/Thimphu", "Asia/Thimphu"),
                            ("Asia/Tokyo", "Asia/Tokyo"),
                            ("Asia/Ulaanbaatar", "Asia/Ulaanbaatar"),
                            ("Asia/Urumqi", "Asia/Urumqi"),
                            ("Asia/Ust-Nera", "Asia/Ust-Nera"),
                            ("Asia/Vientiane", "Asia/Vientiane"),
                            ("Asia/Vladivostok", "Asia/Vladivostok"),
                            ("Asia/Yakutsk", "Asia/Yakutsk"),
                            ("Asia/Yekaterinburg", "Asia/Yekaterinburg"),
                            ("Asia/Yerevan", "Asia/Yerevan"),
                            ("Atlantic/Azores", "Atlantic/Azores"),
                            ("Atlantic/Bermuda", "Atlantic/Bermuda"),
                            ("Atlantic/Canary", "Atlantic/Canary"),
                            ("Atlantic/Cape_Verde", "Atlantic/Cape_Verde"),
                            ("Atlantic/Faroe", "Atlantic/Faroe"),
                            ("Atlantic/Madeira", "Atlantic/Madeira"),
                            ("Atlantic/Reykjavik", "Atlantic/Reykjavik"),
                            ("Atlantic/South_Georgia", "Atlantic/South_Georgia"),
                            ("Atlantic/St_Helena", "Atlantic/St_Helena"),
                            ("Atlantic/Stanley", "Atlantic/Stanley"),
                            ("Australia/Adelaide", "Australia/Adelaide"),
                            ("Australia/Brisbane", "Australia/Brisbane"),
                            ("Australia/Broken_Hill", "Australia/Broken_Hill"),
                            ("Australia/Currie", "Australia/Currie"),
                            ("Australia/Darwin", "Australia/Darwin"),
                            ("Australia/Eucla", "Australia/Eucla"),
                            ("Australia/Hobart", "Australia/Hobart"),
                            ("Australia/Lindeman", "Australia/Lindeman"),
                            ("Australia/Lord_Howe", "Australia/Lord_Howe"),
                            ("Australia/Melbourne", "Australia/Melbourne"),
                            ("Australia/Perth", "Australia/Perth"),
                            ("Australia/Sydney", "Australia/Sydney"),
                            ("Canada/Atlantic", "Canada/Atlantic"),
                            ("Canada/Central", "Canada/Central"),
                            ("Canada/Eastern", "Canada/Eastern"),
                            ("Canada/Mountain", "Canada/Mountain"),
                            ("Canada/Newfoundland", "Canada/Newfoundland"),
                            ("Canada/Pacific", "Canada/Pacific"),
                            ("Europe/Amsterdam", "Europe/Amsterdam"),
                            ("Europe/Andorra", "Europe/Andorra"),
                            ("Europe/Athens", "Europe/Athens"),
                            ("Europe/Belgrade", "Europe/Belgrade"),
                            ("Europe/Berlin", "Europe/Berlin"),
                            ("Europe/Bratislava", "Europe/Bratislava"),
                            ("Europe/Brussels", "Europe/Brussels"),
                            ("Europe/Bucharest", "Europe/Bucharest"),
                            ("Europe/Budapest", "Europe/Budapest"),
                            ("Europe/Busingen", "Europe/Busingen"),
                            ("Europe/Chisinau", "Europe/Chisinau"),
                            ("Europe/Copenhagen", "Europe/Copenhagen"),
                            ("Europe/Dublin", "Europe/Dublin"),
                            ("Europe/Gibraltar", "Europe/Gibraltar"),
                            ("Europe/Guernsey", "Europe/Guernsey"),
                            ("Europe/Helsinki", "Europe/Helsinki"),
                            ("Europe/Isle_of_Man", "Europe/Isle_of_Man"),
                            ("Europe/Istanbul", "Europe/Istanbul"),
                            ("Europe/Jersey", "Europe/Jersey"),
                            ("Europe/Kaliningrad", "Europe/Kaliningrad"),
                            ("Europe/Kiev", "Europe/Kiev"),
                            ("Europe/Lisbon", "Europe/Lisbon"),
                            ("Europe/Ljubljana", "Europe/Ljubljana"),
                            ("Europe/London", "Europe/London"),
                            ("Europe/Luxembourg", "Europe/Luxembourg"),
                            ("Europe/Madrid", "Europe/Madrid"),
                            ("Europe/Malta", "Europe/Malta"),
                            ("Europe/Mariehamn", "Europe/Mariehamn"),
                            ("Europe/Minsk", "Europe/Minsk"),
                            ("Europe/Monaco", "Europe/Monaco"),
                            ("Europe/Moscow", "Europe/Moscow"),
                            ("Europe/Oslo", "Europe/Oslo"),
                            ("Europe/Paris", "Europe/Paris"),
                            ("Europe/Podgorica", "Europe/Podgorica"),
                            ("Europe/Prague", "Europe/Prague"),
                            ("Europe/Riga", "Europe/Riga"),
                            ("Europe/Rome", "Europe/Rome"),
                            ("Europe/Samara", "Europe/Samara"),
                            ("Europe/San_Marino", "Europe/San_Marino"),
                            ("Europe/Sarajevo", "Europe/Sarajevo"),
                            ("Europe/Simferopol", "Europe/Simferopol"),
                            ("Europe/Skopje", "Europe/Skopje"),
                            ("Europe/Sofia", "Europe/Sofia"),
                            ("Europe/Stockholm", "Europe/Stockholm"),
                            ("Europe/Tallinn", "Europe/Tallinn"),
                            ("Europe/Tirane", "Europe/Tirane"),
                            ("Europe/Uzhgorod", "Europe/Uzhgorod"),
                            ("Europe/Vaduz", "Europe/Vaduz"),
                            ("Europe/Vatican", "Europe/Vatican"),
                            ("Europe/Vienna", "Europe/Vienna"),
                            ("Europe/Vilnius", "Europe/Vilnius"),
                            ("Europe/Volgograd", "Europe/Volgograd"),
                            ("Europe/Warsaw", "Europe/Warsaw"),
                            ("Europe/Zagreb", "Europe/Zagreb"),
                            ("Europe/Zaporozhye", "Europe/Zaporozhye"),
                            ("Europe/Zurich", "Europe/Zurich"),
                            ("GMT", "GMT"),
                            ("Indian/Antananarivo", "Indian/Antananarivo"),
                            ("Indian/Chagos", "Indian/Chagos"),
                            ("Indian/Christmas", "Indian/Christmas"),
                            ("Indian/Cocos", "Indian/Cocos"),
                            ("Indian/Comoro", "Indian/Comoro"),
                            ("Indian/Kerguelen", "Indian/Kerguelen"),
                            ("Indian/Mahe", "Indian/Mahe"),
                            ("Indian/Maldives", "Indian/Maldives"),
                            ("Indian/Mauritius", "Indian/Mauritius"),
                            ("Indian/Mayotte", "Indian/Mayotte"),
                            ("Indian/Reunion", "Indian/Reunion"),
                            ("Pacific/Apia", "Pacific/Apia"),
                            ("Pacific/Auckland", "Pacific/Auckland"),
                            ("Pacific/Bougainville", "Pacific/Bougainville"),
                            ("Pacific/Chatham", "Pacific/Chatham"),
                            ("Pacific/Chuuk", "Pacific/Chuuk"),
                            ("Pacific/Easter", "Pacific/Easter"),
                            ("Pacific/Efate", "Pacific/Efate"),
                            ("Pacific/Enderbury", "Pacific/Enderbury"),
                            ("Pacific/Fakaofo", "Pacific/Fakaofo"),
                            ("Pacific/Fiji", "Pacific/Fiji"),
                            ("Pacific/Funafuti", "Pacific/Funafuti"),
                            ("Pacific/Galapagos", "Pacific/Galapagos"),
                            ("Pacific/Gambier", "Pacific/Gambier"),
                            ("Pacific/Guadalcanal", "Pacific/Guadalcanal"),
                            ("Pacific/Guam", "Pacific/Guam"),
                            ("Pacific/Honolulu", "Pacific/Honolulu"),
                            ("Pacific/Johnston", "Pacific/Johnston"),
                            ("Pacific/Kiritimati", "Pacific/Kiritimati"),
                            ("Pacific/Kosrae", "Pacific/Kosrae"),
                            ("Pacific/Kwajalein", "Pacific/Kwajalein"),
                            ("Pacific/Majuro", "Pacific/Majuro"),
                            ("Pacific/Marquesas", "Pacific/Marquesas"),
                            ("Pacific/Midway", "Pacific/Midway"),
                            ("Pacific/Nauru", "Pacific/Nauru"),
                            ("Pacific/Niue", "Pacific/Niue"),
                            ("Pacific/Norfolk", "Pacific/Norfolk"),
                            ("Pacific/Noumea", "Pacific/Noumea"),
                            ("Pacific/Pago_Pago", "Pacific/Pago_Pago"),
                            ("Pacific/Palau", "Pacific/Palau"),
                            ("Pacific/Pitcairn", "Pacific/Pitcairn"),
                            ("Pacific/Pohnpei", "Pacific/Pohnpei"),
                            ("Pacific/Port_Moresby", "Pacific/Port_Moresby"),
                            ("Pacific/Rarotonga", "Pacific/Rarotonga"),
                            ("Pacific/Saipan", "Pacific/Saipan"),
                            ("Pacific/Tahiti", "Pacific/Tahiti"),
                            ("Pacific/Tarawa", "Pacific/Tarawa"),
                            ("Pacific/Tongatapu", "Pacific/Tongatapu"),
                            ("Pacific/Wake", "Pacific/Wake"),
                            ("Pacific/Wallis", "Pacific/Wallis"),
                            ("US/Alaska", "US/Alaska"),
                            ("US/Arizona", "US/Arizona"),
                            ("US/Central", "US/Central"),
                            ("US/Eastern", "US/Eastern"),
                            ("US/Hawaii", "US/Hawaii"),
                            ("US/Mountain", "US/Mountain"),
                            ("US/Pacific", "US/Pacific"),
                            ("UTC", "UTC"),
                        ],
                    ),
                ),
                (
                    "scheduledatetimefield",
                    models.CharField(
                        max_length=128, verbose_name="Schedule Datetime", blank=True
                    ),
                ),
                (
                    "schedulegamefield",
                    models.CharField(
                        max_length=128, verbose_name="Schdule Game", blank=True
                    ),
                ),
                (
                    "schedulerunnersfield",
                    models.CharField(
                        max_length=128, verbose_name="Schedule Runners", blank=True
                    ),
                ),
                (
                    "scheduleestimatefield",
                    models.CharField(
                        max_length=128, verbose_name="Schedule Estimate", blank=True
                    ),
                ),
                (
                    "schedulesetupfield",
                    models.CharField(
                        max_length=128, verbose_name="Schedule Setup", blank=True
                    ),
                ),
                (
                    "schedulecommentatorsfield",
                    models.CharField(
                        max_length=128, verbose_name="Schedule Commentators", blank=True
                    ),
                ),
                (
                    "schedulecommentsfield",
                    models.CharField(
                        max_length=128, verbose_name="Schedule Comments", blank=True
                    ),
                ),
                ("date", models.DateField()),
                (
                    "locked",
                    models.BooleanField(
                        default=False,
                        help_text="Requires special permission to edit this event or anything associated with it",
                    ),
                ),
                (
                    "donationemailtemplate",
                    models.ForeignKey(
                        related_name="event_donation_templates",
                        on_delete=django.db.models.deletion.PROTECT,
                        default=None,
                        blank=True,
                        to="post_office.EmailTemplate",
                        null=True,
                        verbose_name="Donation Email Template",
                    ),
                ),
                (
                    "pendingdonationemailtemplate",
                    models.ForeignKey(
                        related_name="event_pending_donation_templates",
                        on_delete=django.db.models.deletion.PROTECT,
                        default=None,
                        blank=True,
                        to="post_office.EmailTemplate",
                        null=True,
                        verbose_name="Pending Donation Email Template",
                    ),
                ),
            ],
            options={
                "ordering": ("date",),
                "get_latest_by": "date",
                "permissions": (("can_edit_locked_events", "Can edit locked events"),),
            },
        ),
        migrations.CreateModel(
            name="FlowModel",
            fields=[
                (
                    "id",
                    models.ForeignKey(
                        primary_key=True, serialize=False, to=settings.AUTH_USER_MODEL
                    ),
                ),
                ("flow", oauth2client.django_orm.FlowField(null=True)),
            ],
        ),
        migrations.CreateModel(
            name="Log",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(auto_now_add=True, verbose_name="Timestamp"),
                ),
                (
                    "category",
                    models.CharField(
                        default="other", max_length=64, verbose_name="Category"
                    ),
                ),
                ("message", models.TextField(verbose_name="Message", blank=True)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        blank=True,
                        to="tracker.Event",
                        null=True,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True, to=settings.AUTH_USER_MODEL, null=True
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
                "verbose_name": "Log",
                "permissions": (
                    ("can_view_log", "Can view tracker logs"),
                    ("can_change_log", "Can change tracker logs"),
                ),
            },
        ),
        migrations.CreateModel(
            name="PostbackURL",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("url", models.URLField(verbose_name="URL")),
                (
                    "event",
                    models.ForeignKey(
                        related_name="postbacks",
                        on_delete=django.db.models.deletion.PROTECT,
                        verbose_name="Event",
                        to="tracker.Event",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Prize",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=64)),
                ("image", models.URLField(max_length=1024, null=True, blank=True)),
                (
                    "altimage",
                    models.URLField(
                        help_text="A second image to display in situations where the default image is not appropriate (tight spaces, stream, etc...)",
                        max_length=1024,
                        null=True,
                        verbose_name="Alternate Image",
                        blank=True,
                    ),
                ),
                (
                    "imagefile",
                    models.FileField(null=True, upload_to="prizes", blank=True),
                ),
                (
                    "description",
                    models.TextField(max_length=1024, null=True, blank=True),
                ),
                (
                    "shortdescription",
                    models.TextField(
                        help_text="Alternative description text to display in tight spaces",
                        max_length=256,
                        verbose_name="Short Description",
                        blank=True,
                    ),
                ),
                ("extrainfo", models.TextField(max_length=1024, null=True, blank=True)),
                (
                    "estimatedvalue",
                    models.DecimalField(
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                        max_digits=20,
                        blank=True,
                        null=True,
                        verbose_name="Estimated Value",
                    ),
                ),
                (
                    "minimumbid",
                    models.DecimalField(
                        default=Decimal("5.0"),
                        verbose_name="Minimum Bid",
                        max_digits=20,
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "maximumbid",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("5.0"),
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                        max_digits=20,
                        blank=True,
                        null=True,
                        verbose_name="Maximum Bid",
                    ),
                ),
                (
                    "sumdonations",
                    models.BooleanField(default=False, verbose_name="Sum Donations"),
                ),
                (
                    "randomdraw",
                    models.BooleanField(default=True, verbose_name="Random Draw"),
                ),
                (
                    "ticketdraw",
                    models.BooleanField(default=False, verbose_name="Ticket Draw"),
                ),
                (
                    "starttime",
                    models.DateTimeField(
                        null=True, verbose_name="Start Time", blank=True
                    ),
                ),
                (
                    "endtime",
                    models.DateTimeField(
                        null=True, verbose_name="End Time", blank=True
                    ),
                ),
                (
                    "maxwinners",
                    models.IntegerField(
                        default=1,
                        verbose_name="Max Winners",
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "maxmultiwin",
                    models.IntegerField(
                        default=1,
                        verbose_name="Max Wins per Donor",
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "provided",
                    models.CharField(
                        max_length=64, null=True, verbose_name="Provided By", blank=True
                    ),
                ),
                (
                    "provideremail",
                    models.EmailField(
                        max_length=128,
                        null=True,
                        verbose_name="Provider Email",
                        blank=True,
                    ),
                ),
                (
                    "acceptemailsent",
                    models.BooleanField(
                        default=False, verbose_name="Accept/Deny Email Sent"
                    ),
                ),
                (
                    "creator",
                    models.CharField(
                        max_length=64, null=True, verbose_name="Creator", blank=True
                    ),
                ),
                (
                    "creatoremail",
                    models.EmailField(
                        max_length=128,
                        null=True,
                        verbose_name="Creator Email",
                        blank=True,
                    ),
                ),
                (
                    "creatorwebsite",
                    models.CharField(
                        max_length=128,
                        null=True,
                        verbose_name="Creator Website",
                        blank=True,
                    ),
                ),
                (
                    "state",
                    models.CharField(
                        default="PENDING",
                        max_length=32,
                        choices=[
                            ("PENDING", "Pending"),
                            ("ACCEPTED", "Accepted"),
                            ("DENIED", "Denied"),
                            ("FLAGGED", "Flagged"),
                        ],
                    ),
                ),
            ],
            options={
                "ordering": ["event__date", "startrun__starttime", "starttime", "name"],
            },
        ),
        migrations.CreateModel(
            name="PrizeCategory",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(unique=True, max_length=64)),
            ],
            options={
                "verbose_name": "Prize Category",
                "verbose_name_plural": "Prize Categories",
            },
        ),
        migrations.CreateModel(
            name="PrizeTicket",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "amount",
                    models.DecimalField(
                        max_digits=20,
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                    ),
                ),
                (
                    "donation",
                    models.ForeignKey(
                        related_name="tickets",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="tracker.Donation",
                    ),
                ),
                (
                    "prize",
                    models.ForeignKey(
                        related_name="tickets",
                        on_delete=django.db.models.deletion.PROTECT,
                        to="tracker.Prize",
                    ),
                ),
            ],
            options={
                "ordering": ["-donation__timereceived"],
                "verbose_name": "Prize Ticket",
            },
        ),
        migrations.CreateModel(
            name="PrizeWinner",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "pendingcount",
                    models.IntegerField(
                        default=1,
                        help_text="The number of pending wins this donor has on this prize.",
                        verbose_name="Pending Count",
                        validators=[tracker.validators.positive],
                    ),
                ),
                (
                    "acceptcount",
                    models.IntegerField(
                        default=0,
                        help_text="The number of copied this winner has won and accepted.",
                        verbose_name="Accept Count",
                        validators=[tracker.validators.positive],
                    ),
                ),
                (
                    "declinecount",
                    models.IntegerField(
                        default=0,
                        help_text="The number of declines this donor has put towards this prize. Set it to the max prize multi win amount to prevent this donor from being entered from future drawings.",
                        verbose_name="Decline Count",
                        validators=[tracker.validators.positive],
                    ),
                ),
                (
                    "sumcount",
                    models.IntegerField(
                        default=1,
                        help_text="The total number of prize instances associated with this winner",
                        verbose_name="Sum Counts",
                        editable=False,
                        validators=[tracker.validators.positive],
                    ),
                ),
                (
                    "emailsent",
                    models.BooleanField(
                        default=False, verbose_name="Notification Email Sent"
                    ),
                ),
                (
                    "shippingemailsent",
                    models.BooleanField(
                        default=False, verbose_name="Shipping Email Sent"
                    ),
                ),
                (
                    "trackingnumber",
                    models.CharField(
                        max_length=64, verbose_name="Tracking Number", blank=True
                    ),
                ),
                (
                    "shippingstate",
                    models.CharField(
                        default="PENDING",
                        max_length=64,
                        verbose_name="Shipping State",
                        choices=[("PENDING", "Pending"), ("SHIPPED", "Shipped")],
                    ),
                ),
                (
                    "shippingcost",
                    models.DecimalField(
                        decimal_places=2,
                        validators=[
                            tracker.validators.positive,
                            tracker.validators.nonzero,
                        ],
                        max_digits=20,
                        blank=True,
                        null=True,
                        verbose_name="Shipping Cost",
                    ),
                ),
                (
                    "prize",
                    models.ForeignKey(
                        to="tracker.Prize", on_delete=django.db.models.deletion.PROTECT
                    ),
                ),
                (
                    "winner",
                    models.ForeignKey(
                        to="tracker.Donor", on_delete=django.db.models.deletion.PROTECT
                    ),
                ),
            ],
            options={"verbose_name": "Prize Winner",},
        ),
        migrations.CreateModel(
            name="SpeedRun",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                ("name", models.CharField(max_length=64, editable=False)),
                (
                    "deprecated_runners",
                    models.CharField(
                        max_length=1024, verbose_name="*DEPRECATED* Runners", blank=True
                    ),
                ),
                ("description", models.TextField(max_length=1024, blank=True)),
                ("starttime", models.DateTimeField(verbose_name="Start Time")),
                ("endtime", models.DateTimeField(verbose_name="End Time")),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        default=tracker.models.event.LatestEvent,
                        to="tracker.Event",
                    ),
                ),
                (
                    "runners",
                    models.ManyToManyField(to="tracker.Donor", null=True, blank=True),
                ),
            ],
            options={
                "ordering": ["event__date", "starttime"],
                "verbose_name": "Speed Run",
            },
        ),
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        verbose_name="ID",
                        serialize=False,
                        auto_created=True,
                        primary_key=True,
                    ),
                ),
                (
                    "prepend",
                    models.CharField(
                        max_length=64, verbose_name="Template Prepend", blank=True
                    ),
                ),
                ("user", models.ForeignKey(to=settings.AUTH_USER_MODEL, unique=True)),
            ],
            options={
                "verbose_name": "User Profile",
                "permissions": (
                    ("show_rendertime", "Can view page render times"),
                    ("show_queries", "Can view database queries"),
                    ("sync_schedule", "Can sync the schedule"),
                    ("can_search", "Can use search url"),
                ),
            },
        ),
        migrations.AddField(
            model_name="prize",
            name="category",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                blank=True,
                to="tracker.PrizeCategory",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="prize",
            name="endrun",
            field=models.ForeignKey(
                related_name="prize_end",
                on_delete=django.db.models.deletion.PROTECT,
                verbose_name="End Run",
                blank=True,
                to="tracker.SpeedRun",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="prize",
            name="event",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                default=tracker.models.event.LatestEvent,
                to="tracker.Event",
            ),
        ),
        migrations.AddField(
            model_name="prize",
            name="startrun",
            field=models.ForeignKey(
                related_name="prize_start",
                on_delete=django.db.models.deletion.PROTECT,
                verbose_name="Start Run",
                blank=True,
                to="tracker.SpeedRun",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="donorprizeentry",
            name="prize",
            field=models.ForeignKey(
                to="tracker.Prize", on_delete=django.db.models.deletion.PROTECT
            ),
        ),
        migrations.AddField(
            model_name="donorcache",
            name="event",
            field=models.ForeignKey(blank=True, to="tracker.Event", null=True),
        ),
        migrations.AddField(
            model_name="donation",
            name="donor",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                blank=True,
                to="tracker.Donor",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="donation",
            name="event",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                default=tracker.models.event.LatestEvent,
                to="tracker.Event",
            ),
        ),
        migrations.AddField(
            model_name="bid",
            name="event",
            field=models.ForeignKey(
                related_name="bids",
                on_delete=django.db.models.deletion.PROTECT,
                blank=True,
                to="tracker.Event",
                help_text="Required for top level bids if Run is not set",
                null=True,
                verbose_name="Event",
            ),
        ),
        migrations.AddField(
            model_name="bid",
            name="parent",
            field=mptt.fields.TreeForeignKey(
                related_name="options",
                on_delete=django.db.models.deletion.PROTECT,
                blank=True,
                editable=False,
                to="tracker.Bid",
                null=True,
                verbose_name="Parent",
            ),
        ),
        migrations.AddField(
            model_name="bid",
            name="speedrun",
            field=models.ForeignKey(
                related_name="bids",
                on_delete=django.db.models.deletion.PROTECT,
                verbose_name="Run",
                blank=True,
                to="tracker.SpeedRun",
                null=True,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="speedrun", unique_together=set([("name", "event")]),
        ),
        migrations.AlterUniqueTogether(
            name="prizewinner", unique_together=set([("prize", "winner")]),
        ),
        migrations.AlterUniqueTogether(
            name="prizeticket", unique_together=set([("prize", "donation")]),
        ),
        migrations.AlterUniqueTogether(
            name="prize", unique_together=set([("name", "event")]),
        ),
        migrations.AlterUniqueTogether(
            name="donorprizeentry", unique_together=set([("prize", "donor")]),
        ),
        migrations.AlterUniqueTogether(
            name="donorcache", unique_together=set([("event", "donor")]),
        ),
        migrations.AlterUniqueTogether(
            name="donationbid", unique_together=set([("bid", "donation")]),
        ),
        migrations.AlterUniqueTogether(
            name="bid", unique_together=set([("event", "name", "speedrun", "parent")]),
        ),
    ]
