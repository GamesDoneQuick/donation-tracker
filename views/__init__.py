from tracker.views.auth import __all__ as all_auth_views
from tracker.views.auth import *  # noqa

from tracker.views.public import __all__ as all_public_views
from tracker.views.public import *  # noqa

from tracker.views.api import __all__ as all_api_views
from tracker.views.api import *  # noqa

from tracker.views.donateviews import __all__ as all_donate_views
from tracker.views.donateviews import *  # noqa

from tracker.views.user import __all__ as all_user_views
from tracker.views.user import *  # noqa

from tracker.views.commands import __all__ as all_command_views
from tracker.views.commands import *  # noqa


__all__ = (
    all_auth_views
    + all_public_views
    + all_api_views
    + all_donate_views
    + all_user_views
    + all_command_views
)
