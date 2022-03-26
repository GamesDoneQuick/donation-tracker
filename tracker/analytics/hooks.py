"""
This module defines hooks for various parts of different model lifetimes using
Django's signal system as a stepping stone to integrating these more directly
in appropriate views. For example, donations being read or ignored would instead
be handled dedicated views for those actions.

These actions are better handled in views because they have access to additional
relevant information from the request, like which user performed the action,
granularity about where the request came from (i.e., admin view vs an api call),
and more importantly failure states if a model was incorrectly changed.
"""
from django.db.models import signals
from django.dispatch import receiver

from tracker.models import DonationBid
from . import analytics, AnalyticsEventTypes


def track_bid_applied(instance: DonationBid):
    bid = instance.bid
    donation = instance.donation
    analytics.track(
        AnalyticsEventTypes.BID_APPLIED,
        {
            'timestamp': donation.timereceived.isoformat(),
            'event_id': instance.event_id,
            'incentive_id': instance.bid_id,
            'parent_id': bid.parent_id,
            'donation_id': instance.donation_id,
            'amount': instance.amount,
            'total_donation_amount': donation.amount,
            'incentive_goal_amount': bid.goal,
            'incentive_current_amount': bid.total,
            # TODO: Set this to an actual value when tracking moves
            # to the separate view functions.
            'added_manually': False,
        },
    )


@receiver(signals.post_save, sender=DonationBid)
def donation_bid_receiver(sender, instance, created):
    # TODO: This should move to `donateviews.process_form` to track bids that
    # are created as part of the original donation, and a separate admin view
    # to track bids applied manually by a donation processor.
    if created:
        track_bid_applied(instance)
