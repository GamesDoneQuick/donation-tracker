import os

import post_office.mail
from django.contrib.auth import get_user_model

from tracker import settings

AuthUser = get_user_model()


def _readtemplate(filename):
    with open(
        os.path.join(os.path.dirname(__file__), 'templates/tracker/email', filename),
        'r',
    ) as infile:
        return infile.read()


def default_prize_winner_template_name():
    return getattr(settings, 'PRIZE_WINNER_EMAIL_TEMPLATE_NAME', 'default_prize_winner')


def default_prize_winner_template():
    return post_office.models.EmailTemplate(
        name=default_prize_winner_template_name(),
        subject='You won {{ claims|pluralize:"a prize, some prizes" }} at {{ event.name }}',
        description="""A basic template for automailing prize winners. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined and must be used are:
event -- the event for the set of prizes
winner -- the winner donor object
claims -- the the list of PrizeClaim objects for this donor
requires_shipping -- whether or not any of the claims will require shipping
reply_address -- the reply address specified on the form
accept_deadline -- the date by which we need a response or we will re-roll

The following DEPRECATED variables are also defined, and will be removed at some point in the future:
prize_wins -- deprecated alias for claims
multi -- true if there are multiple prizes, false if there is only one (use `claims|length > 1` or `claims|pluralize` instead)
prize_count -- the number of claims (use `claims|length` instead)
""",
        html_content=_readtemplate('default_prize_winner.html'),
    )


def default_prize_contributor_template_name():
    return getattr(
        settings,
        'PRIZE_CONTRIBUTOR_EMAIL_TEMPLATE_NAME',
        'default_prize_contributor',
    )


def default_prize_contributor_template():
    return post_office.models.EmailTemplate(
        name=default_prize_contributor_template_name(),
        subject='{{ event.name }} Prize Contributor Notification',
        description="""A basic template for automailing back prize accept/reject notifications. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined and must be used are:
user_index_url -- the user index url (i.e. /user/index)
event -- the event object.
handler -- the User object of the person responsible for shipping
accepted_prizes -- A list of all accepted prizes.
denied_prizes  -- A list of all denied prizes.
reply_address -- The address to reply to on this e-mail
""",
        html_content=_readtemplate('default_prize_contributor.html'),
    )


def default_prize_winner_accept_template_name():
    return getattr(
        settings,
        'WINNER_ACCEPT_EMAIL_TEMPLATE_NAME',
        'default_prize_winner_accept',
    )


def default_prize_winner_accept_template():
    return post_office.models.EmailTemplate(
        name=default_prize_winner_accept_template_name(),
        description="""A basic template for automailing when prizes are accepted by winners and require the handler to ship them. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined and must be used are:
user_index_url -- the user index url (i.e. /user/index)
claims -- the list of PrizeClaim objects that were accepted
handler -- the user that is handling shipping the prizes
reply_address -- the address to reply to (will be overridden if the event has a prize coordinator)

The following optional variable is also defined:
event -- the event for the set of prizes

The following DEPRECATED variables are also defined, and will be removed at some point in the future:
prize_wins -- alias for claims
prize_count -- the number of prizes in the list (use `claims|length` instead)
""",
        subject='Your Prize{{ claims|pluralize }} {{ claims|pluralize:"Has,Have" }} Been Accepted',
        html_content=_readtemplate('default_prize_winner_accept.html'),
    )


def default_prize_shipping_template_name():
    return getattr(settings, 'SHIPPING_EMAIL_TEMPLATE_NAME', 'default_prize_shipping')


def default_prize_shipping_template():
    return post_office.models.EmailTemplate(
        name=default_prize_shipping_template_name(),
        description="""A basic template for automailing when prizes are shipped or non-physical prizes (e.g. game keys) are awarded. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined and must be used are:
claims -- the list of PrizeClaims
winner -- the donor that won the prizes
reply_address -- the address to reply to

The following optional variables are also defined:
shipped -- if any of the prizes were shipped
awarded -- if any of the prizes do not require shipping (game keys, etc)
event -- the event for the set of prizes

The following DEPRECATED variables are also defined, and will be removed at some point in the future:
prize_wins -- alias for claims
prize_count -- the number of prizes in the list (use `claims|length` instead)
""",
        subject='Prize{{ claims|pluralize }} {% if shipped %}Shipped{% endif %}{% if shipped and awarded %} or {% endif %}{% if awarded %}Awarded{% endif %}',
        html_content=_readtemplate('default_prize_shipping.html'),
    )
