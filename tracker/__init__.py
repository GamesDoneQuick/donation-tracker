import json
import os

from .settings import TrackerSettings

settings = TrackerSettings()

default_app_config = 'tracker.apps.TrackerAppConfig'

__bare_version__ = '3.3.1.dev0'

__version__ = (
    __bare_version__.replace('dev0', tag)
    if (tag := os.environ.get('BUILD_NUMBER', ''))
    else __bare_version__
)

try:
    with open(os.path.join(os.path.dirname(__file__), '../package.json')) as pkg:
        assert json.load(pkg)['version'] == __bare_version__
except IOError:
    pass
