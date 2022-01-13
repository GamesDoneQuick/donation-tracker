# Django Donation Tracker

## Requirements

- Python 3.6, 3.7 (3.8 is untested)

Additionally, if you are planning on developing, and/or building the JS bundles yourself:

- Node 12.x
- `yarn` (`npm i -g yarn`)
- `pre-commit` (`pip install pre-commit`)

If you need to isolate your development environment, some combination of `direnv`, `pyenv`, `nvm`, and/or `asdf` will be
very helpful.

## Deploying

This app shouldn't require any special treatment to deploy, though depending on which feature set you are using, extra
steps will be required. You should be able to install it with pip, either from PyPI (preferred so that you don't have
to build the JS bundles yourself), GitHub, or locally.

For further reading on what else your server needs to look like:

- [Deploying Django](https://docs.djangoproject.com/en/2.2/howto/deployment/)
- [Deploying Django Channels](https://channels.readthedocs.io/en/latest/deploying.html)
- [Configuring Post Office](https://github.com/ui/django-post_office#management-commands) (needed to send emails)
- [Using Celery with Django](https://docs.celeryproject.org/en/stable/django/first-steps-with-django.html) (optional)
- [Daemonizing Celery](https://docs.celeryproject.org/en/stable/userguide/daemonizing.html) (optional)

Docker should also work but support is still in the experimental phases.

### Configuration

The Donation Tracker adds a few configuration options.

#### HAS_CELERY

Type: `bool`

Default: `False`

Controls whether or not to try and use Celery. Certain tasks will be queued up as asynchronous if this setting is
turned on, but it requires extra setup and for smaller events the performance impact is pretty minor.

#### GIANTBOMB_API_KEY

Type: `str`

Default: `None`

Used for the `cache_giantbomb_info` management command. See that command for further details.

#### PRIVACY_POLICY_URL

Type: `str`

Default: `''`

If present, shown on the Donation page. You should probably have one of these, but this README is not legal advice.

#### SWEEPSTAKES_URL

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

### Testing Your Deploy (incomplete)

- PayPal currently requires the receiver account to have IPNs turned on so that payment can be confirmed
  - The sandbox sends IPNs, so you should not need to use the IPN simulator unless you really want to
- There is a Diagnostics page on the admin, accessible if you are a Django superuser, it will let you test or monitor
  various pieces of Tracker functionality, which can give you early hints that something isn't working right

## Development Quick Start

Start up a new Django Project like the [Django Tutorial](https://docs.djangoproject.com/en/2.2/intro/tutorial01/).

- `pip install django~=2.2`
- `django-admin startproject tracker_development`
- `cd tracker_development`

Clone the Git repo and install it in edit mode:

- `git clone git@github.com:RTAinJapan/donation-tracker`
- `pip install -e donation-tracker`

Install remaining development dependencies:

- `cd donation-tracker`
- `yarn`
- `pre-commit install`
- `pre-commit install --hook-type pre-push`

Add the following apps to the `INSTALLED_APPS` section of `tracker_development/settings.py`:

```
    'channels',
    'post_office',
    'paypal.standard.ipn',
    'tracker',
    'timezone_field',
    'ajax_select',
    'mptt',
```

Add the following parameter in `setting.py`:

```
DOMAIN = "server hostname"
```

Add the following chunk somewhere in `settings.py`:

```python
from tracker import ajax_lookup_channels
AJAX_LOOKUP_CHANNELS = ajax_lookup_channels.AJAX_LOOKUP_CHANNELS
ASGI_APPLICATION = 'tracker_development.routing.application'
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
```

Create a file next called `routing.py` next to `settings.py` and put the following in it:

```python
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import path

import tracker.routing

application = ProtocolTypeRouter({
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                [path('tracker/', URLRouter(tracker.routing.websocket_urlpatterns))]
            )
        )
    ),
})
```

Edit the `tracker_development/urls.py` file to look something like this:

```python
from django.contrib import admin
from django.urls import path, include

import tracker.urls
import ajax_select.urls

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin/lookups/', include(ajax_select.urls)),
    path('tracker/', include(tracker.urls, namespace='tracker')),
]
```

In the main project folder:

- `python manage.py migrate`
- `python manage.py compilemessages`

  - It needs `gettext`. For example, `apt-get install -y gettext libgettextpo-dev`

- `python manage.py createsuperuser`

  - create superuser by following the dialog

- `python manage.py runserver`

In a separate shell, in the `donation-tracker` folder:

- `yarn start`

If everything boots up correctly, you should be able to visit the [Index Page](http://localhost:8080/tracker).
Additionally, you should be able to open the [Websocket Test Page](http://localhost:8080/tracker/websocket_test/) and
see the heartbeat. If the page loads but the pings don't work, Channels isn't set up correctly. The
[Channels Documentation](https://channels.readthedocs.io/en/latest/installation.html) may be helpful.

## Contributing

This project uses [`pre-commit`](https://pre-commit.com/) to run linters and other checks before every commit.

If you followed the instructions above, `pre-commit` should run the appropriate hooks every time you commit or push.

_Note:_ You _can_ bypass these checks by adding `--no-verify` when you commit or push, though this is highly
discouraged in most cases. In the future, CI tests may fail if any of these checks are not satisfied.
