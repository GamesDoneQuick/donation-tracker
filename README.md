# Django Donation Tracker

## Requirements

- Python 3.9 to 3.13
- Django 4.2, 5.1, or 5.2

Additionally, if you are planning on developing, and/or building the JS bundles yourself:

- Node (only LTS versions are officially supported, currently 18, 20, and 22)
- `yarn` (`npm i -g yarn`)
- `pre-commit` (`pip install pre-commit`)

If you need to isolate your development environment, some combination of `direnv`, `pyenv`, `nvm`, and/or `asdf` will be
very helpful.

## Deploying

This app shouldn't require any special treatment to deploy, though depending on which feature set you are using, extra
steps will be required. You should be able to install it with pip, either from GitHub, or locally. e.g.

`pip install git+https://github.com/GamesDoneQuick/donation-tracker.git@master`

Or after downloading or checking out locally:

`pip install ./donation-tracker`

For further reading on what else your server needs to look like:

- [Deploying Django](https://docs.djangoproject.com/en/dev/howto/deployment/)
- [Deploying Django Channels](https://channels.readthedocs.io/en/latest/deploying.html)
- [Configuring Post Office](https://github.com/ui/django-post_office#management-commands) (needed to send emails)
- [Using Celery with Django](https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html) (optional)
- [Daemonizing Celery](https://docs.celeryproject.org/en/stable/userguide/daemonizing.html) (optional)

Docker and Kubernetes have also been shown to work, but setting that up is beyond the scope of this document.

If `tqdm` is installed, certain long-running migrations and commands will use it to display progress on your console.
This can be disabled by setting the environment variable `TRACKER_DISABLE_TQDM` to any non-blank value.

**Ensure that `PAYPAL_TEST` is present in your settings.** It should be set to True for development/testing and False
for production mode.

### Configuration

The Donation Tracker adds several configuration options.

#### TRACKER_HAS_CELERY (deprecated alias: HAS_CELERY)

Type: `bool`

Default: `False`

Controls whether to try and use Celery. Certain tasks will be queued up as asynchronous if this setting is turned on,
but it requires extra setup and for smaller events the performance impact is pretty minor.

#### TRACKER_GIANTBOMB_API_KEY (deprecated alias: GIANTBOMB_API_KEY)

Type: `str`

Default: `''`

Used for the `cache_giantbomb_info` management command. See that command for further details.

#### TRACKER_PRIVACY_POLICY_URL (deprecated alias: PRIVACY_POLICY_URL)

Type: `str`

Default: `''`

If present, shown on the Donation page. You should probably have one of these, but this README is not legal advice.

#### TRACKER_SWEEPSTAKES_URL (deprecated alias: SWEEPSTAKES_URL)

Type: `str`

Default: `''`

If present, shown in several prize-related pages. This is REQUIRED if you offer any prizes from your events, and will
disable a lot of prize functionality if it's not set. This is for legal reasons because it's very easy to run afoul of
local sweepstakes laws. This README is not legal advice, however, so you should contact a lawyer before you give away
prizes.

#### TRACKER_PAGINATION_LIMIT

Type: `int`

Default: `500`

Allows you to override the number of results a user can fetch from the API at a single time, or will be returned by
default. Attempting to set a `limit=` param in a `search` higher than this value will return an error instead.

#### TRACKER_LOGO

Type: `str`

Default: `''`

Allows you to place a logo asset in the navbar for public facing pages.

#### TRACKER_ENABLE_BROWSABLE_API

Type: `bool`

Default: `settings.DEBUG`

Allows you to enable or disable the DRF browsable API renderer on the v2 endpoints. By default, it's disabled in
production mode and enabled in development.

This can potentially override DRF's own explicit or default settings, but only in that it will remove the renderer in
question if it's in the list.

#### TRACKER_CONTRIBUTORS_URL

Type: `str`

Default: `'https://github.com/GamesDoneQuick/donation-tracker/graphs/contributors'`

If set, will display this link in the common template footer. If you want to hide the link you can set it to a blank
string.

#### TRACKER_PAYPAL_MAX_DONATE_AGE

Type: `int`

Default: `60`

The maximum age in seconds for which a signed donation payload is considered valid. When a user donates via the standard
PayPal form, the server will generate a signed payload string as a confirmation step, salted with the user's IP. If the
payload is older than the specified age, it is no longer considered valid and will not redirect them to PayPal. This
does not affect how much time the user has to complete the PayPal flow.

#### TRACKER_PAYPAL_SIGNATURE_PREFIX

Type: `str`

Default: `'tracker'`

To make it easier to determine if an IPN is from the Tracker or not, all outgoing PayPal requests
use a signed payload in the `custom` field, using this prefix, and salted with the amount of the
donation. Do not change this while an event is running or in-flight IPNs will not validate properly.
Must be between 1 and 8 characters long, inclusive. You probably don't need to change this unless
the recipient is already using the prefix for some other purpose.

#### TRACKER_PAYPAL_ALLOW_OLD_IPN_FORMAT

Type: `bool`

Default: `False`

Previously, outgoing PayPal donations were tagged with a custom string with the donation ID embedded, without any
other sort of prefix. If you still have incoming IPNs using this format, set this to True. Most IPNs reconcile
within an hour, except in the case of e-checks, which can take several days. Chargebacks can also complicate this.
Generally speaking you should leave this as False unless you have recently upgraded to code that expects the new
format. If set to False, IPNs using this format will be logged but not otherwise acted upon.

#### TRACKER_PAYPAL_MAXIMUM_AMOUNT

Type: `int`

Default: `60000`

PayPal enforces a maximum amount in USD per transaction, depending on a lot of arcane factors. See [PayPal Limits
Explained](https://www.paypal.com/us/brc/article/understanding-account-limitations) for more information. As of this
writing the absolute maximum is $60,000 USD, but if you wish to change the default limit, especially if most of your
events are in a currency other than USD, you can do so here. This can also be overridden on a per-event basis. Note
that this is a hint, not a hard enforcement, and if the donor or the recipient is not capable of the desired transfer,
PayPal will give you an error.

#### TRACKER_REGISTRATION_FROM_EMAIL

Type: `str` (must pass `EmailValidator`)

Default: `settings.DEFAULT_FROM_EMAIL`

If you want to override the email address that registration emails come from, you can do so with this setting.

#### TRACKER_VOLUNTEER_REGISTRATION_FROM_EMAIL

Type: `str` (must pass `EmailValidator`)

Default: `settings.TRACKER_REGISTRATION_FROM_EMAIL`

If you want to override the default email address that volunteer import registration emails (i.e. the `Send Volunteer
Emails` via the Event Admin action dropdown) come from, you can do so with this setting. You can still override it in
the form itself before doing the import.

#### TRACKER_PUBLIC_SITE_ID

Type: `int`

Default: `SITE_ID` if `django.contrib.sites` is installed, else `None`

If specified, allows you to override the domain used for generating certain urls. Right now it's just prize emails and
"View on Site" admin links.

If set, requires the `django.contrib.sites` application to be installed, or it will be ignored.

Expects the domain from the specified site in one of three formats:
- `one.com` - bare domain, treated the same as `//one.com`
- `//two.com` - domain with scheme-relative specifier, will use scheme from the request
- `https://three.com` - domain with scheme, will override the scheme from the request

#### TRACKER_DEFAULT_PRIZE_COORDINATOR

Type: `str`

Default: None

If specified, new events will default to this username for the Prize Coordinator field. Note that the value is
case-sensitive if using the standard User model. If the User cannot be found, this value will be ignored.

### Prizes

The Tracker has a comprehensive prize flow once configured properly. You'll need to configure the sweepstakes URL as
mentioned above, as well as ensure that your outgoing email configuration works. The Diagnostics page can be useful for
this.

The Tracker has support for three types of prizes:

#### Physical

Just what they sound like. They need to be shipped to the winner. If the contributor is expected to handle shipping,
they are also the handler. You may wish to have one central location that your contributors send prizes to, in which
case the handler should be assigned to one of your staff members upon acceptance of the prize.

#### Digital

Mostly the same as physical, except that no shipping is required. An example might be "Custom Digital Art" where the
winner chooses what is drawn. These prizes should have `requiresshipping` set to `false`, and they will skip some of
the later lifecycle steps.

#### Digital Keys

A variant of digital prizes. After they are drawn *they cannot be automatically reassigned*, and move to the `shipped`
part of the prize lifecycle. Before sending out the notifications you may wish to validate the list of winners.
Indicated in the DB by the `key_code` field. You can import a list of keys to a given prize with the `Import Prize Keys`
admin action.

#### Prize Lifecycle, Including Email

You can consider prizes to be in one of thirteen states. If you have the necessary API permissions (`tracker.view_prize`
and `tracker.view_prizeclaim`) you can query the prize API endpoint with the parameter `?lifecycle={state}` to get a
list of prizes in certain states. If the parameter is repeated, you can retrieve multiple states in a single query. Note
that prizes that have multiple copies may be in multiple states at once. When this parameter is provided, an
additional `lifecycle` field will be returned. The exception to this is `archived`, where it will return the state as
if the event were not archived, to make it easier to tell where the prize would otherwise be. You may also leave the
parameter blank (i.e. `?lifecycle=`) if you just want to see the lifecycle without filtering.

Suggested example email templates can be set up with the Django management command `default_email_templates`. See that
command for further details, but the short version is that you probably want `default_email_templates -ao` to create
the standard set of examples, or `-aop {your_prefix}` to create them with your custom prefix. The Prize mail pages will
not let you choose a template whose name starts with `default`, and will verify that a) there are no invalid variables
in the template and b) certain required variables are used.

#### Pending

API state: `pending`
Needs email: No

A user (contributor) has submitted a prize via the form, and is in a 'PENDING' state. Somebody with prize editing
access should either accept or deny the prize, possibly after cleaning up the information.

If you are letting the contributor handle shipping, you can leave the `handler` field alone, but if you are, for
example, asking your contributors to send the prizes to a central location, you should edit the handler field, likely
to your event's Prize Coordinator. For certain prizes this may not be practical, but that's the fun of logistics!

#### Accepted/Denied

API state: `notify_contributor`
Needs email: Yes

The prize has been accepted or denied, but the contributor has not been notified. `Mail Prize Contributors` will show a
list of all pending emails, grouped by contributor.

#### Denied w/notification

API state: `denied`
Needs email: No

Same as `notify_contributor` when a prize has been denied and the notification is sent.

#### Accepted w/notification, not ready to draw

API state: `accepted`
Needs email: No

Same as `notify_contributor` when a prize has been accepted and the notification is sent, and is not ready to draw. The
standard state of prizes while an event is ongoing.

#### Ready to draw

API state: `ready`
Needs email: No

Accepted prizes that are ready to draw because:

- the event's prize window has closed (after waiting for write-ins, etc.)
- there are not enough claimed or pending-but-not-expired winners for the number of copies

The latter condition is true when either no winners exist, or some of the existing winners have either explicitly
declined the prize, or the accept deadline has passed.

Note: Currently, a winner can still claim a prize that has passed its deadline *so long as it has not been redrawn*.
This is an implementation detail and is subject to change at any time.

The difference between `accepted` and `ready` depends on the precise time of the request, or the value of the `time`
parameter, e.g. `?time=2020-01-08` or `?time=2020-01-08T06:00:00-4:00`. Anything that looks like an ISO timestamp
should work.

#### Drawn

API state: `drawn`
Needs email: Yes

The prize has been drawn, and a winner picked, but the winner has not been notified. `Mail Prize Winners` will show a
list of prizes in this state, grouped by winner.

#### Drawn w/notification

API state: `winner_notified`
Needs email: No

Same as above, except the notification email has been sent.

For physical prizes, the winner will be asked to fill in or verify address information.

For digital prizes, the winner will be asked to accept or decline the prize so that the handler can contact them.

Key prizes skip this step and instead move to `shipped`.

#### Claimed

API state: `claimed`
Needs email: Yes

The winner has claimed at least one copy of the prize, but the handler has not been notified. `Mail Prize Winner Accept
Notifications` will show a list of prizes in this state, grouped by handler. Note that if the handler is the same as the
event's `prizecoordinator`, it will skip this step and move to `needs_shipping`.

#### Claimed w/notification, needs shipping information

API state: `needs_shipping`
Needs email: No

Same as above, but either the notification has been sent, or the handler is the same as the event's Prize Coordinator,
and the prize needs to be shipped. If the handler is not the prize coordinator, the notification email from the previous
step will provide instructions on how to submit shipping information via a custom Tracker form.

Digital prizes skip this step and instead move to `completed`.

#### Shipped/Awarded

API state: `shipped`
Needs email: Yes

For physical prizes, the claim has been marked as `SHIPPED`, possibly with tracking information.

For key prizes, it means that the key has been assigned to a winner. It cannot be re-assigned without manual
intervention at this step, for example if the winner is not supposed to be eligible for the prize. If the winner doesn't
want the key, it's a better idea to tell them to pass it on themselves rather than try and reassign it.

#### Completed

API state: `completed`
Needs email: No

For physical or key prizes, the prize has been marked as shipped or awarded and the winner notified.

For digital prizes, the handler has been notified of the prize claim. At that point it is the handler's responsibility
to contact the winner and work out any remaining details.

#### Archived

API state: `archived`

If a prize is not in either the `pending`, `notify_contributor`, `denied` or `complete` part of its lifecycle, but the
event it's attached to has been archived, it will be in this state. Usually this is a sign that something was left
unfinished, so you may wish to investigate further and figure out why. The API will still list the lifecycle as if the
prize were not archived, but querying for this will restrict it to only the prizes that are archived.

### Event Configuration

`Screening Mode` has three options:

- `Host Only` - donations are sent to the `Read Donations` page immediately, but will still show as pending on public
  pages once the donation has either been read or skipped/ignored. If your donation volume is low enough that the host
  can handle screening on their own, you can probably use this.
- `One Pass` - donations require one extra layer of moderation via `Process Donations` before they will show up in
  `Read Donations`. This is the default mode.
- `Two Pass` - donations require two layers of moderation before showing up on the read page. When this mode is active
  you will need users with the `Can Send to Reader` permission to use the `Confirm` mode in `Process Donations` before
  anything will show up on `Read Donations`. Most events probably won't need this, as it is intended for high volume
  events (e.g. AGDQ/SGDQ).

### Testing Your Deploy (WIP)

- PayPal currently requires the receiver account to have IPNs turned on so that payment can be confirmed.
  - You do -not- need to set the confirmation URL to your Tracker instance, as the callback url is part of the outgoing
    payload, but it does need to be set to -some- URL that returns a 200 response, or PayPal will continuously retry
    sending the IPN.
  - The sandbox sends IPNs so you should be able to use the standard flow to test if your Tracker instance is publicly
    accessible. All donations received this way will be flagged as test donations and will not be counted when you turn
    sandbox mode off.
  - You can also use the IPN simulator. The custom payload follows the format `{prefix}:{id}:{signature}`, where
    `prefix` is the value of `TRACKER_PAYPAL_SIGNATURE_PREFIX`, `id` is the numeric ID of the donation row, and
    `signature` is a signed JSON block from [Django's Cryptographic Signing](https://docs.djangoproject.com/en/dev/topics/signing/)
    with an `id` key that matches the previous parameter, and salted with the amount of the donation as a string, e.g.
    `123.45`. You can get a sample signature block from the admin page for any PayPal donation.
- There is a Diagnostics page on the admin, accessible if you are a Django superuser, it will let you test or monitor
  various pieces of Tracker functionality, which can give you early hints that something isn't working right.
  - If Secure Request is False even when you are using HTTPS, Django might not be parsing your proxy headers correctly.
    [SECURE_PROXY_SSL_HEADER](https://docs.djangoproject.com/en/5.2/ref/settings/#secure-proxy-ssl-header) is the most
    likely culprit.

## Development Quick Start

Clone the Git repo and install it in edit mode:

- `git clone git@github.com:GamesDoneQuick/donation-tracker`
- `pip install -e donation-tracker[development]`

Start up a new Django Project like the [Django Tutorial](https://docs.djangoproject.com/en/dev/intro/tutorial01/).

- `pip install django~=5.0` (if you need a specific version of Django)
- `django-admin startproject tracker_development`

Install remaining development dependencies:

- `cd donation-tracker`
- `yarn`
- `pre-commit install`
- `pre-commit install --hook-type pre-push`

Add the `daphne` app **to the top of** the `INSTALLED_APPS` section of `tracker_development/settings.py`, then add the following after all other apps:

```
    'channels',
    'post_office',
    'paypal.standard.ipn',
    'tracker',
    'rest_framework',
    'timezone_field',
    'mptt',
```

To enable analytics tracking, add the following to the `MIDDLEWARE` section of `tracker_development/settings.py`:

```
    'tracker.analytics.middleware.AnalyticsMiddleware',
```

NOTE: The analytics middleware is only a client, and does not track any information locally. Instead, it expects an analytics server to be running and will simply send out HTTP requests to it when enabled. More information is available in `tracker/analytics/README.md`.

Add the following chunk somewhere in `settings.py`:

```python
ASGI_APPLICATION = 'tracker_development.routing.application'
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
PAYPAL_TEST = True

# Only required if analytics tracking is enabled
TRACKER_ANALYTICS_INGEST_HOST = 'http://localhost:5000'
TRACKER_ANALYTICS_NO_EMIT = False
TRACKER_ANALYTICS_TEST_MODE = False
TRACKER_ANALYTICS_ACCESS_KEY = 'someanalyticsaccesskey or None'
```

Create a file next called `routing.py` next to `settings.py` and put the following in it:

```python
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path
from django.core.asgi import get_asgi_application

import tracker.routing

application = ProtocolTypeRouter({
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                [path('tracker/', URLRouter(tracker.routing.websocket_urlpatterns))]
            )
        )
    ),
    'http': get_asgi_application()
})
```

Edit the `tracker_development/urls.py` file to look something like this:

```python
from django.contrib import admin
from django.urls import path, include

import tracker.urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('tracker/', include(tracker.urls, namespace='tracker')),
]
```

In the `tracker_development` folder:

- `python manage.py migrate`
- `python manage.py createsuperuser`
- `python manage.py runserver`

In a separate shell, in the `donation-tracker` folder:

- `yarn start`

If everything boots up correctly, you should be able to visit the [Index Page](http://localhost:8080/tracker).
You should also be able to open the [Diagnostics Page](http://localhost:8080/admin/tracker/event/diagnostics) and run the websocket test.
If the page loads but the pings don't work, Channels isn't set up correctly. The
[Channels Documentation](https://channels.readthedocs.io/en/latest/installation.html) may be helpful.

Additional environment keys can assist with JS bundle development and deployment.

The following keys are considered boolean and will activate if any non-empty value is set for them.

- `TRACKER_REDUX_LOGGING` - log every Redux action to the console via `redux-logger`
- `TRACKER_DEBUG` - runs some extra checks on certain code and hooks, will also be true if `WEBPACK_SERVE` or
  `WEBPACK_DEV_SERVER` are set to any non-empty value
- `NO_MANIFEST` - do not build the HTML templates, only really useful for running the Jasmine tests
- `ANALYZE` - activates [Webpack Bundle Analyzer](https://github.com/webpack-contrib/webpack-bundle-analyzer)
- `SOURCE_MAPS` - activates source maps, defaults to on when running in dev mode

Other variables that take string values:

- `STATIC_ROOT` - defaults to `/static/gen`, i.e. `http://yourserver/static/gen`, if your static files are deployed at
  a different path you'll need to override this

Same with the following, except they only matter for development:

- `TRACKER_API_HOST` - if you want to send `/tracker/api` requests to a different host, you can override this, will
  prefer this over `TRACKER_HOST`
- `TRACKER_HOST` - if you want to send most HTTP/WS requests to a different host, you can override this - check
  `webpack.config.js` to see a full list

## Contributing

This project uses [`pre-commit`](https://pre-commit.com/) to run linters and other checks before every commit.

If you followed the instructions above, `pre-commit` should run the appropriate hooks every time you commit or push.

_Note:_ You _can_ bypass these checks by adding `--no-verify` when you commit or push, though this is highly
discouraged in most cases. CI runs the same checks as the hooks do, and will cause pipeline to fail if you bypass
a genuine failure.
