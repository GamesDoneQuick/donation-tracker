# Django Donation Tracker

## Requirements

- Python 3.6, 3.7 (3.8 is untested)

Additionally, if you are planning on developing:

- Node 12.x
- `yarn` (`npm i -g yarn`)
- `pre-commit` (`pip install pre-commit`)

If you need to isolate your development environment, some combination of `direnv`, `pyenv`, `nvm`, and/or `asdf` will be
very helpful.

## Deploying

This app shouldn't require any special treatment to deploy. You should be able to install it with pip, either from PyPI
(preferred so that you don't have to build the JS bundles yourself), GitHub, or locally.

For further reading on what else your server needs to look like:

- [Deploying Django](https://docs.djangoproject.com/en/2.2/howto/deployment/)
- [Deploying Django Channels](https://channels.readthedocs.io/en/latest/deploying.html)

Docker should also work but support is still in the experimental phases.

## Development Quick Start

Start up a new Django Project like the [Django Tutorial](https://docs.djangoproject.com/en/2.2/intro/tutorial01/).

- `pip install django~=2.2`
- `django-admin startproject tracker_development`
- `cd tracker_development`

Clone the Git repo and install it in edit mode:

- `git clone git@github.com:GamesDoneQuick/donation-tracker`
- `pip install -e donation-tracker`

Install remaining development dependencies:

- `cd donation-tracker`
- `yarn`
- `pre-commit install`
- `pre-commit install --hook-type pre-push`

Add the following apps to the `INSTALLED_APPS` section of `tracker_development/settings.py`:

- `channels`
- `post_office`
- `paypal.standard.ipn`
- `tracker`
- `timezone_field`
- `ajax_select`
- `mptt`

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

Edit the `urls.py` file to look something like this:

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

- `python manage.py runserver`

In a separate shell, in the `donation-tracker` folder:

- `yarn start`

If everything boots up correctly, you should be able to visit the [Index Page](http://localhost:8080/tracker). Additionally, you should be able to open the [Websocket Test Page](http://localhost:8080/tracker/websocket_test/) and see the heartbeat. If the page loads but the pings don't work, Channels isn't set up correctly. The [Channels Documentation](https://channels.readthedocs.io/en/latest/installation.html) may be helpful.

## Contributing

This project uses [`pre-commit`](https://pre-commit.com/) to run linters and other checks before every commit.

If you followed the instructions above, `pre-commit` should run the appropriate hooks every time you commit or push.

_Note:_ You _can_ bypass these checks by adding `--no-verify` when you commit or push, though this is highly discouraged in most cases. In the future, CI tests may fail if any of these checks are not satisfied.

(Note: I'm not a lawyer, somebody clean this up, please.)
By opening a Pull Request on this repository, you acknowledge that your contributions will be further licensed by Games Done Quick LLC under the Apache 2.0 License (see LICENSE for details).
