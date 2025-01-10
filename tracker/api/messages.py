from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotAuthenticated, PermissionDenied

GENERIC_NOT_FOUND = _(
    'That resource does not exist or you do not have permission to view it.'
)

NO_GENERAL_SEARCH = _('That endpoint does not support `q` searches.')
NO_GENERAL_SEARCH_CODE = 'no_general_search'
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
UNAUTHORIZED_FIELD_MODIFICATION = _(
    'You do not have permission to set that value on that field.'
)
UNAUTHORIZED_FIELD_MODIFICATION_CODE = 'unauthorized_field_modification'
UNAUTHORIZED_LOCKED_EVENT = _(
    'You do not have permission to edit objects associated with locked events.'
)
UNAUTHORIZED_LOCKED_EVENT_CODE = 'unauthorized_locked_event'
UNAUTHORIZED_FEED = _('You do not have permission to view that feed.')
UNAUTHORIZED_FEED_CODE = 'unauthorized_feed'
UNAUTHORIZED_OBJECT = _('You do not have permission to view that object.')
UNAUTHORIZED_OBJECT_CODE = 'unauthorized_object'
EVENT_READ_ONLY = _('Event is read-only after create for that model.')
EVENT_READ_ONLY_CODE = 'event_read_only'
INVALID_PK = _('Could not find a related object with the primary key `{pk}`.')
INVALID_PK_CODE = 'invalid_pk'
INVALID_NATURAL_KEY = _(
    'Could not find a related object with the natural key `{natural_key}`.'
)
INVALID_NATURAL_KEY_CODE = 'invalid_natural_key'
INVALID_NATURAL_KEY_LENGTH = _(
    'Natural key was the incorrect length, expected {expected}, got {actual}.'
)
INVALID_NATURAL_KEY_LENGTH_CODE = 'invalid_natural_key_length'
INVALID_LOOKUP_TYPE = _('Could not parse that input as a valid relational key.')
INVALID_LOOKUP_TYPE_CODE = 'invalid_lookup_type'
NO_NESTED_CREATES = _('That model creation cannot be nested from this endpoint.')
NO_NESTED_CREATES_CODE = 'no_nested_creates'
NO_NESTED_UPDATES = _(
    'Nested models are only writeable on creation, use the endpoint for that specific model instead.'
)
NO_NESTED_UPDATES_CODE = 'no_nested_updates'
ANCHOR_FIELD = _('`event` and `order` fields are implicit if specifying `anchor`.')
ANCHOR_FIELD_CODE = 'invalid_anchor_sibling'
INVALID_ANCHOR = _('Specified anchor is not ordered.')
INVALID_ANCHOR_CODE = 'invalid_anchor'
PERMISSION_DENIED = PermissionDenied.default_detail
PERMISSION_DENIED_CODE = PermissionDenied.default_code
NOT_AUTHENTICATED = NotAuthenticated.default_detail
NOT_AUTHENTICATED_CODE = NotAuthenticated.default_code
INVALID_TIMESTAMP = _('Provided timestamp could not be parsed.')
INVALID_TIMESTAMP_CODE = 'invalid_timestamp'
INVALID_BID_APPROVAL_STATE = _('Bid state must be pending')
INVALID_BID_APPROVAL_STATE_CODE = 'invalid_bid_approval_state'
