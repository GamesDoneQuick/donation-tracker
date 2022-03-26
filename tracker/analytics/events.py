import enum


class AnalyticsEventTypes(enum.Enum):
    BID_APPLIED = 'bid_applied'
    INCENTIVE_OPENED = 'incentive_opened'
    INCENTIVE_MET = 'incentive_met'
    DONATION_SUBMITTED = 'donation_submitted'
    DONATION_PENDING = 'donation_pending'
    DONATION_COMPLETED = 'donation_completed'
    DONATION_CANCELLED = 'donation_cancelled'
    REQUEST_SERVED = 'request_served'
