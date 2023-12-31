from django.utils.translation import gettext_lazy as _

GENERIC_NOT_FOUND = _(
    'That resource does not exist or you do not have permission to view it.'
)

MALFORMED_SEARCH_PARAMETER = _('At least one search parameter was malformed.')
MALFORMED_SEARCH_PARAMETER_SPECIFIC = _('`%s` parameter was malformed.')
MALFORMED_SEARCH_PARAMETER_CODE = 'malformed_search_parameter'
UNAUTHORIZED_FILTER_PARAM = _('You are not allowed to perform that search.')
UNAUTHORIZED_FILTER_PARAM_CODE = 'unauthorized_search_parameter'
UNAUTHORIZED_FIELD = _('You are not allowed to query that field.')
UNAUTHORIZED_FIELD_CODE = 'unauthorized_field'
INVALID_FEED = _('`%s` is not a valid feed.')
INVALID_FEED_CODE = 'invalid_feed'
INVALID_SEARCH_PARAMETER_CODE = 'invalid_search_parameter'
UNAUTHORIZED_LOCKED_EVENT = _(
    'You do not have permission to edit objects associated with locked events.'
)
UNAUTHORIZED_LOCKED_EVENT_CODE = 'unauthorized_locked_event'
UNAUTHORIZED_FEED = _('You do not have permission to view that feed.')
UNAUTHORIZED_FEED_CODE = 'unauthorized_feed'
UNAUTHORIZED_OBJECT = _('You do not have permission to view that object.')
UNAUTHORIZED_OBJECT_CODE = 'unauthorized_object'
