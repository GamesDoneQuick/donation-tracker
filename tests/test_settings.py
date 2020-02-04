import os

from tracker import ajax_lookup_channels

DOMAIN = 'testserver'
SECRET_KEY = 'ForTestingPurposesOnly'
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.staticfiles',
    'post_office',
    'paypal.standard.ipn',
    'tracker',
    'timezone_field',
    'ajax_select',
    'mptt',
]
DATABASES = {
    'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': 'testdb.sqlite',},
}
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(os.path.dirname(__file__), 'static')
MEDIA_ROOT = os.path.join(os.path.dirname(__file__), 'media')
USE_TZ = True
TIME_ZONE = 'America/Denver'
ROOT_URLCONF = 'tests.urls'
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
            ],
            'debug': True,
            'string_if_invalid': 'Invalid Variable: %s',
        },
    },
]
MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.common.CommonMiddleware',
)
AJAX_LOOKUP_CHANNELS = ajax_lookup_channels.AJAX_LOOKUP_CHANNELS
CACHES = {'default': {'BACKEND': 'django.core.cache.backends.dummy.DummyCache',}}
ASGI_APPLICATION = 'tests.routing.application'
CHANNEL_LAYERS = {'default': {'BACKEND': 'channels.layers.InMemoryChannelLayer'}}
