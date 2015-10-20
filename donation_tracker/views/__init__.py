from donation_tracker.views.auth import __all__ as all_auth_views
from donation_tracker.views.auth import *

from donation_tracker.views.public import __all__ as all_public_views
from donation_tracker.views.public import *

from donation_tracker.views.api import __all__ as all_api_views
from donation_tracker.views.api import *

from donation_tracker.views.donateviews import __all__ as all_donate_views
from donation_tracker.views.donateviews import *

from donation_tracker.views.prizeviews import __all__ as all_prize_views
from donation_tracker.views.prizeviews import *

from donation_tracker.views.commands import __all__ as all_command_views
from donation_tracker.views.commands import *

__all__ = all_auth_views + all_public_views + all_api_views + all_donate_views + all_prize_views + all_command_views
