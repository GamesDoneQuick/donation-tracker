import enum


class AnalyticsEventTypes(str, enum.Enum):
    BID_APPLIED = 'bid_applied'
    INCENTIVE_OPENED = 'incentive_opened'
    INCENTIVE_MET = 'incentive_met'
    DONATION_RECEIVED = 'donation_received'
    DONATION_PENDING = 'donation_pending'
    DONATION_COMPLETED = 'donation_completed'
    DONATION_CANCELLED = 'donation_cancelled'
    DONATION_COMMENT_APPROVED = 'donation_comment_approved'
    DONATION_COMMENT_DENIED = 'donation_comment_denied'
    DONATION_COMMENT_FLAGGED = 'donation_comment_flagged'
    DONATION_COMMENT_SENT_TO_READER = 'donation_comment_sent_to_reader'
    DONATION_COMMENT_UNPROCESSED = 'donation_comment_unprocessed'
    DONATION_COMMENT_AUTOMOD_DENIED = 'donation_comment_automod_denied'
    DONATION_COMMENT_PINNED = 'donation_comment_pinned'
    DONATION_COMMENT_UNPINNED = 'donation_comment_unpinned'
    DONATION_COMMENT_READ = 'donation_commment_read'
    DONATION_COMMENT_IGNORED = 'donation_commment_ignored'
    DONATION_MOD_COMMENT_EDITED = 'donation_mod_comment_edited'
    REQUEST_SERVED = 'request_served'
