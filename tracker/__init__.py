import json
import os

try:
    from .settings import TrackerSettings

    settings = TrackerSettings()

    default_app_config = 'tracker.apps.TrackerAppConfig'
except ImportError:
    # happens when setuptools is trying to evaluate the version
    pass

__bare_version__ = '3.3.1.dev0'

if __tag__ := os.environ.get('BUILD_NUMBER', ''):
    __version__ = __bare_version__.replace('dev0', __tag__)
else:
    __version__ = __bare_version__

try:
    with open(os.path.join(os.path.dirname(__file__), '../package.json')) as pkg:
        assert json.load(pkg)['version'] == __bare_version__
except IOError:
    pass
