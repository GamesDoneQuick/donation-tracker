import datetime
import itertools
import os

import post_office.mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db.models import Q, F

import tracker.viewutil as viewutil
from tracker.models import *

AuthUser = get_user_model()


def _readtemplate(filename):
    with open(
        os.path.join(os.path.dirname(__file__), "templates/tracker/email", filename),
        "r",
    ) as infile:
        return infile.read()


def get_event_default_sender_email(event):
    if event and event.prizecoordinator:
        return event.prizecoordinator.email
    else:
        return viewutil.get_default_email_from_user()


def event_sender_replyto_defaults(event, sender=None, replyTo=None):
    if sender == None:
        sender = get_event_default_sender_email(event)
    if replyTo == None:
        replyTo = sender
    return sender, replyTo


def prize_winners_with_email_pending(event):
    return PrizeWinner.objects.filter(
        prize__event=event, pendingcount__gt=0, emailsent=False
    )


def default_prize_winner_template_name():
    return getattr(
        settings, "PRIZE_WINNER_EMAIL_TEMPLATE_NAME", "default_prize_winner_template"
    )


def default_prize_winner_template():
    return post_office.models.EmailTemplate(
        name=default_prize_winner_template_name(),
        subject="{% if multi %}You won some prizes at {{ event.name }}{% else %}You won a prize at {{ event.name }}{% endif %}",
        description="""A basic template for automailing prize winners. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
event -- the event for the set of prizes
winner -- the winner donor object
prizes -- the list of prizes this donor has won
accept_deadline -- the date by which we need a response or we will re-roll
prize_wins -- the list of PrizeWinner objects for this donor (if you need the additional information)
requires_shipping -- true if any of the prizes require shipping information
multi -- true if there are multiple prizes, false if there is only one (used for plurality branches)
prize_count -- the number of prizes won
reply_address -- the reply address specified on the form (will be overridden if the event has a prize coordinator)
""",
        html_content=_readtemplate("default_prize_winner_template.html"),
    )


def automail_prize_winners(
    event,
    prizeWinners,
    mailTemplate,
    sender=None,
    replyTo=None,
    domain=settings.DOMAIN,
    verbosity=0,
    dry_run=False,
):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)

    winnerDict = {}
    for prizeWinner in prizeWinners:
        if prizeWinner.winner.id in list(winnerDict.keys()):
            winList = winnerDict[prizeWinner.winner.id]
        else:
            winList = []
            winnerDict[prizeWinner.winner.id] = winList
        winList.append(prizeWinner)
    for winnerk, prizesWon in winnerDict.items():
        winner = prizesWon[0].winner
        prizesList = []
        minAcceptDeadline = min(
            itertools.chain(
                [
                    x
                    for x in [pw.accept_deadline_date() for pw in prizesWon]
                    if x != None
                ],
                [datetime.date.max],
            )
        )

        for prizeWon in prizesWon:
            prizesList.append(prizeWon.prize)
        formatContext = {
            "event": event,
            "winner": winner,
            "prize_wins": prizesWon,
            "multi": len(prizesWon) > 1,
            "prize_count": len(prizesWon),
            "reply_address": replyTo,
            "accept_deadline": minAcceptDeadline,
        }

        if not dry_run:
            post_office.mail.send(
                recipients=[winner.email],
                sender=sender,
                template=mailTemplate,
                context=formatContext,
                headers={"Reply-to": replyTo},
            )

        message = "Mailed donor {0} for prize wins {1}".format(
            winner.id, list([pw.id for pw in prizesWon])
        )

        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log("prize", message, event)
            for prizeWon in prizesWon:
                prizeWon.emailsent = True
                prizeWon.save()


def prizes_with_submission_email_pending(event):
    return Prize.objects.filter(
        Q(state="ACCEPTED") | Q(state="DENIED"), acceptemailsent=False, event=event
    )


def default_activate_prize_handlers_template_name():
    return getattr(
        settings,
        "ACTIVATE_PRIZE_HANDLER_EMAIL_TEMPLATE_NAME",
        "default_activate_prize_handler_template",
    )


def default_activate_prize_handlers_template():
    return post_office.models.EmailTemplate(
        name=default_activate_prize_handlers_template_name(),
        subject="{{ event.name }} Prize Contributor Account Activation",
        description="""A template to automail prize handlers to activate their account on the site, such that they can deal with prize accept/shipping stuff. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
event -- the event object
handler -- the User objects of the person responsible for shipping
register_url -- the user registration URL (i.e. /user/register)
prize_set -- the set of prizes they are responsible
prize_count -- the number of prizes in the set
reply_address -- the address to reply to
""",
        html_content=_readtemplate("default_activate_prize_handlers.html"),
    )


def automail_inactive_prize_handlers(
    event,
    inactiveUsers,
    mailTemplate,
    sender=None,
    replyTo=None,
    domain=settings.DOMAIN,
    verbosity=0,
    dry_run=False,
):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)
    for inactiveUser in inactiveUsers:
        eventPrizes = list(
            Prize.objects.filter(handler=inactiveUser, event=event, state="ACCEPTED")
        )
        formatContext = {
            "event": event,
            "handler": inactiveUser,
            "register_url": domain + reverse("tracker:register"),
            "prize_set": eventPrizes,
            "prize_count": len(eventPrizes),
            "reply_address": replyTo,
        }
        if not dry_run:
            post_office.mail.send(
                recipients=[inactiveUser.email],
                sender=sender,
                template=mailTemplate,
                context=formatContext,
                headers={"Reply-to": replyTo},
            )
        message = "Mailed prize handler {0} (#{1}) for account activation".format(
            inactiveUser, inactiveUser.id
        )
        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log("prize", message, event)


def get_event_inactive_prize_handlers(event):
    return AuthUser.objects.filter(
        is_active=False, prize__event=event, prize__state="ACCEPTED"
    ).distinct()


def default_prize_contributor_template_name():
    return getattr(
        settings,
        "PRIZE_CONTRIBUTOR_EMAIL_TEMPLATE_NAME",
        "default_prize_contributor_template",
    )


def default_prize_contributor_template():
    return post_office.models.EmailTemplate(
        name=default_prize_contributor_template_name(),
        subject="{{ event.name }} Prize Contributor Notification",
        description="""A basic template for automailing back prize accept/reject notifications. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
event -- the event object.
handler -- the User object of the person responsible for shipping
accepted_prizes -- A list of all accepted prizes.
denied_prizes  -- A list of all denied prizes.
reply_address -- The address to reply to on this e-mail
user_index_url -- the user index url (i.e. /user/index)
""",
        html_content=_readtemplate("default_prize_contributor.html"),
    )


def automail_prize_contributors(
    event,
    prizes,
    mailTemplate,
    domain=settings.DOMAIN,
    sender=None,
    replyTo=None,
    verbosity=0,
    dry_run=False,
):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)

    handlerDict = {}
    for prize in prizes:
        if prize.handler:
            prizeList = handlerDict.setdefault(prize.handler, [])
            prizeList.append(prize)
    for handler, prizeList in handlerDict.items():
        denied = list([prize for prize in prizeList if prize.state == "DENIED"])
        formatContext = {
            "user_index_url": domain + reverse("tracker:user_index"),
            "event": event,
            "handler": handler,
            "accepted_prizes": list(
                [prize for prize in prizeList if prize.state == "ACCEPTED"]
            ),
            "denied_prizes": list(
                [prize for prize in prizeList if prize.state == "DENIED"]
            ),
            "reply_address": replyTo,
        }
        if not dry_run:
            post_office.mail.send(
                recipients=[handler.email],
                sender=sender,
                template=mailTemplate,
                context=formatContext,
                headers={"Reply-to": replyTo},
            )
        message = "Mailed prize handler {0} for prizes {1}".format(
            handler.id, list([p.id for p in prizeList])
        )
        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log("prize", message, event)
            for prize in prizeList:
                prize.acceptemailsent = True
                prize.save()


def prizes_with_winner_accept_email_pending(event):
    return PrizeWinner.objects.filter(
        Q(prize__event=event)
        & Q(prize__state="ACCEPTED")
        & Q(acceptcount__gt=F("acceptemailsentcount"))
    )


def default_prize_winner_accept_template_name():
    return getattr(
        settings,
        "WINNER_ACCEPT_EMAIL_TEMPLATE_NAME",
        "default_prize_winner_accept_template",
    )


def default_prize_winner_accept_template():
    return post_office.models.EmailTemplate(
        name=default_prize_winner_accept_template_name(),
        description="""A basic template for automailing when prizes are accepted by winners. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
user_index_url -- the user index url (i.e. /user/index)
prize_wins -- the list of PrizeWinner objects that were accepted
prize_count -- the number of prizes in the list
handler -- the user that is handling shipping the prizes
event -- the event for the set of prizes
reply_address -- the address to reply to (will be overridden if the event has a prize coordinator)
""",
        subject='Your Prize{{ prize_count|pluralize }} {{ prize_count|pluralize:"Has:Have" }} Been Accepted',
        html_content=_readtemplate("default_prize_winner_accept.html"),
    )


def automail_winner_accepted_prize(
    event,
    prizeWinners,
    mailTemplate,
    domain=settings.DOMAIN,
    sender=None,
    replyTo=None,
    verbosity=0,
    dry_run=False,
):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)

    handlerDict = {}
    for prizeWinner in prizeWinners:
        if prizeWinner.prize.handler:
            prizeList = handlerDict.setdefault(prizeWinner.prize.handler, [])
            prizeList.append(prizeWinner)
    for handler, prizeList in handlerDict.items():
        formatContext = {
            "user_index_url": domain + reverse("tracker:user_index"),
            "prize_wins": prizeList,
            "prize_count": len(prizeList),
            "handler": handler,
            "event": event,
            "reply_address": replyTo,
        }
        if not dry_run:
            post_office.mail.send(
                recipients=[handler.email],
                sender=sender,
                template=mailTemplate,
                context=formatContext,
                headers={"Reply-to": replyTo},
            )
        message = "Mailed handler {0} for prize accepts {1}".format(
            handler.id, list([pw.id for pw in prizeList])
        )
        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log("prize", message, event)
            for prizeWinner in prizeList:
                prizeWinner.acceptemailsentcount = prizeWinner.acceptcount
                prizeWinner.save()


def prizes_with_shipping_email_pending(event):
    return PrizeWinner.objects.filter(
        Q(prize__event=event) & Q(shippingstate="SHIPPED") & Q(shippingemailsent=False)
    )


def default_prize_shipping_template_name():
    return getattr(
        settings, "SHIPPING_EMAIL_TEMPLATE_NAME", "default_prize_shipping_template"
    )


def default_prize_shipping_template():
    return post_office.models.EmailTemplate(
        name=default_prize_shipping_template_name(),
        description="""A basic template for automailing when prizes are shipped or keys are awarded. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
prize_wins -- the list PrizeWinner objects
prize_count -- the number of prizes in the list
winner -- the donor that won the prizes
event -- the event for the set of prizes
reply_address -- the address to reply to (will be overridden if the event has a prize coordinator)
""",
        subject="Prize{{ prize_count|pluralize }} Shipped",
        html_content=_readtemplate("default_prize_shipping.html"),
    )


def automail_shipping_email_notifications(
    event,
    prizeWinners,
    mailTemplate,
    domain=settings.DOMAIN,
    sender=None,
    replyTo=None,
    verbosity=0,
    dry_run=False,
):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)

    winnerDict = {}
    for prizeWinner in prizeWinners:
        prizeList = winnerDict.setdefault(prizeWinner.winner, [])
        prizeList.append(prizeWinner)
    for winner, prizeList in winnerDict.items():
        formatContext = {
            "prize_wins": prizeList,
            "prize_count": len(prizeList),
            "winner": winner,
            "event": event,
            "reply_address": replyTo,
        }
        if not dry_run:
            post_office.mail.send(
                recipients=[winner.email],
                sender=sender,
                template=mailTemplate,
                context=formatContext,
                headers={"Reply-to": replyTo},
            )
        message = "Mailed donor {0} for prizes shipped {1}".format(
            winner.id, list([pw.id for pw in prizeList])
        )
        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log("prize", message, event)
            for prizeWinner in prizeList:
                prizeWinner.shippingemailsent = True
                prizeWinner.save()
