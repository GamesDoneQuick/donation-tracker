import datetime
import itertools
import os

import post_office.mail
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q, F
from django.urls import reverse

import tracker.viewutil as viewutil
from tracker.models import Prize, PrizeWinner

AuthUser = get_user_model()


def _readtemplate(filename):
    with open(
        os.path.join(os.path.dirname(__file__), 'templates/tracker/email', filename),
        'r',
    ) as infile:
        return infile.read()


def get_event_default_sender_email(event):
    if event and event.prizecoordinator:
        return event.prizecoordinator.email
    else:
        return viewutil.get_default_email_from_user()


def event_sender_replyto_defaults(event, sender=None, reply_to=None):
    if sender is None:
        sender = get_event_default_sender_email(event)
    if reply_to is None:
        reply_to = sender
    return sender, reply_to


def prize_winners_with_email_pending(event):
    return PrizeWinner.objects.filter(
        prize__event=event, pendingcount__gt=0, emailsent=False
    )


def default_prize_winner_template_name():
    return getattr(
        settings, 'PRIZE_WINNER_EMAIL_TEMPLATE_NAME', 'default_prize_winner_template'
    )


def default_prize_winner_template():
    return post_office.models.EmailTemplate(
        name=default_prize_winner_template_name(),
        subject='{% if multi %}You won some prizes at {{ event.name }}{% else %}You won a prize at {{ event.name }}{% endif %}',
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
        html_content=_readtemplate('default_prize_winner_template.html'),
    )


def automail_prize_winners(
    event,
    prize_winners,
    mail_template,
    sender=None,
    reply_to=None,
    domain=settings.DOMAIN,
    verbosity=0,
    dry_run=False,
):
    sender, reply_to = event_sender_replyto_defaults(event, sender, reply_to)

    winner_dict = {}
    for prize_winner in prize_winners:
        if prize_winner.winner.id in list(winner_dict.keys()):
            win_list = winner_dict[prize_winner.winner.id]
        else:
            win_list = []
            winner_dict[prize_winner.winner.id] = win_list
        win_list.append(prize_winner)
    for winnerk, prizes_won in winner_dict.items():
        winner = prizes_won[0].winner
        prizes_list = []
        min_accept_deadline = min(
            itertools.chain(
                [
                    x
                    for x in [pw.accept_deadline_date() for pw in prizes_won]
                    if x is not None
                ],
                [datetime.date.max],
            )
        )

        for prize_won in prizes_won:
            prizes_list.append(prize_won.prize)
        format_context = {
            'event': event,
            'winner': winner,
            'prize_wins': prizes_won,
            'multi': len(prizes_won) > 1,
            'prize_count': len(prizes_won),
            'reply_address': reply_to,
            'accept_deadline': min_accept_deadline,
        }

        if not dry_run:
            post_office.mail.send(
                recipients=[winner.email],
                sender=sender,
                template=mail_template,
                context=format_context,
                headers={'Reply-to': reply_to},
            )

        message = 'Mailed donor {0} for prize wins {1}'.format(
            winner.id, list([pw.id for pw in prizes_won])
        )

        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log('prize', message, event)
            for prize_won in prizes_won:
                prize_won.emailsent = True
                prize_won.save()


def prizes_with_submission_email_pending(event):
    return Prize.objects.filter(
        Q(state='ACCEPTED') | Q(state='DENIED'), acceptemailsent=False, event=event
    )


def default_activate_prize_handlers_template_name():
    return getattr(
        settings,
        'ACTIVATE_PRIZE_HANDLER_EMAIL_TEMPLATE_NAME',
        'default_activate_prize_handler_template',
    )


def default_activate_prize_handlers_template():
    return post_office.models.EmailTemplate(
        name=default_activate_prize_handlers_template_name(),
        subject='{{ event.name }} Prize Contributor Account Activation',
        description="""A template to automail prize handlers to activate their account on the site, such that they can deal with prize accept/shipping stuff. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
event -- the event object
handler -- the User objects of the person responsible for shipping
register_url -- the user registration URL (i.e. /user/register)
prize_set -- the set of prizes they are responsible
prize_count -- the number of prizes in the set
reply_address -- the address to reply to
""",
        html_content=_readtemplate('default_activate_prize_handlers.html'),
    )


def automail_inactive_prize_handlers(
    event,
    inactive_users,
    mail_template,
    sender=None,
    reply_to=None,
    domain=settings.DOMAIN,
    verbosity=0,
    dry_run=False,
):
    sender, reply_to = event_sender_replyto_defaults(event, sender, reply_to)
    for inactive_user in inactive_users:
        event_prizes = list(
            Prize.objects.filter(handler=inactive_user, event=event, state='ACCEPTED')
        )
        format_context = {
            'event': event,
            'handler': inactive_user,
            'register_url': domain + reverse('tracker:register'),
            'prize_set': event_prizes,
            'prize_count': len(event_prizes),
            'reply_address': reply_to,
        }
        if not dry_run:
            post_office.mail.send(
                recipients=[inactive_user.email],
                sender=sender,
                template=mail_template,
                context=format_context,
                headers={'Reply-to': reply_to},
            )
        message = 'Mailed prize handler {0} (#{1}) for account activation'.format(
            inactive_user, inactive_user.id
        )
        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log('prize', message, event)


def get_event_inactive_prize_handlers(event):
    return AuthUser.objects.filter(
        is_active=False, prize__event=event, prize__state='ACCEPTED'
    ).distinct()


def default_prize_contributor_template_name():
    return getattr(
        settings,
        'PRIZE_CONTRIBUTOR_EMAIL_TEMPLATE_NAME',
        'default_prize_contributor_template',
    )


def default_prize_contributor_template():
    return post_office.models.EmailTemplate(
        name=default_prize_contributor_template_name(),
        subject='{{ event.name }} Prize Contributor Notification',
        description="""A basic template for automailing back prize accept/reject notifications. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
event -- the event object.
handler -- the User object of the person responsible for shipping
accepted_prizes -- A list of all accepted prizes.
denied_prizes  -- A list of all denied prizes.
reply_address -- The address to reply to on this e-mail
user_index_url -- the user index url (i.e. /user/index)
""",
        html_content=_readtemplate('default_prize_contributor.html'),
    )


def automail_prize_contributors(
    event,
    prizes,
    mail_template,
    domain=settings.DOMAIN,
    sender=None,
    reply_to=None,
    verbosity=0,
    dry_run=False,
):
    sender, reply_to = event_sender_replyto_defaults(event, sender, reply_to)

    handler_dict = {}
    for prize in prizes:
        if prize.handler:
            prize_list = handler_dict.setdefault(prize.handler, [])
            prize_list.append(prize)
    for handler, prize_list in handler_dict.items():
        format_context = {
            'user_index_url': domain + reverse('tracker:user_index'),
            'event': event,
            'handler': handler,
            'accepted_prizes': list(
                [prize for prize in prize_list if prize.state == 'ACCEPTED']
            ),
            'denied_prizes': list(
                [prize for prize in prize_list if prize.state == 'DENIED']
            ),
            'reply_address': reply_to,
        }
        if not dry_run:
            post_office.mail.send(
                recipients=[handler.email],
                sender=sender,
                template=mail_template,
                context=format_context,
                headers={'Reply-to': reply_to},
            )
        message = 'Mailed prize handler {0} for prizes {1}'.format(
            handler.id, list([p.id for p in prize_list])
        )
        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log('prize', message, event)
            for prize in prize_list:
                prize.acceptemailsent = True
                prize.save()


def prizes_with_winner_accept_email_pending(event):
    return PrizeWinner.objects.filter(
        Q(prize__event=event)
        & Q(prize__state='ACCEPTED')
        & Q(acceptcount__gt=F('acceptemailsentcount'))
    )


def default_prize_winner_accept_template_name():
    return getattr(
        settings,
        'WINNER_ACCEPT_EMAIL_TEMPLATE_NAME',
        'default_prize_winner_accept_template',
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
        html_content=_readtemplate('default_prize_winner_accept.html'),
    )


def automail_winner_accepted_prize(
    event,
    prize_winners,
    mail_template,
    domain=settings.DOMAIN,
    sender=None,
    reply_to=None,
    verbosity=0,
    dry_run=False,
):
    sender, reply_to = event_sender_replyto_defaults(event, sender, reply_to)

    handler_dict = {}
    for prize_winner in prize_winners:
        if prize_winner.prize.handler:
            prize_list = handler_dict.setdefault(prize_winner.prize.handler, [])
            prize_list.append(prize_winner)
    for handler, prize_list in handler_dict.items():
        format_context = {
            'user_index_url': domain + reverse('tracker:user_index'),
            'prize_wins': prize_list,
            'prize_count': len(prize_list),
            'handler': handler,
            'event': event,
            'reply_address': reply_to,
        }
        if not dry_run:
            post_office.mail.send(
                recipients=[handler.email],
                sender=sender,
                template=mail_template,
                context=format_context,
                headers={'Reply-to': reply_to},
            )
        message = 'Mailed handler {0} for prize accepts {1}'.format(
            handler.id, list([pw.id for pw in prize_list])
        )
        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log('prize', message, event)
            for prize_winner in prize_list:
                prize_winner.acceptemailsentcount = prize_winner.acceptcount
                prize_winner.save()


def prizes_with_shipping_email_pending(event):
    return PrizeWinner.objects.filter(
        Q(prize__event=event) & Q(shippingstate='SHIPPED') & Q(shippingemailsent=False)
    )


def default_prize_shipping_template_name():
    return getattr(
        settings, 'SHIPPING_EMAIL_TEMPLATE_NAME', 'default_prize_shipping_template'
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
        subject='Prize{{ prize_count|pluralize }} Shipped',
        html_content=_readtemplate('default_prize_shipping.html'),
    )


def automail_shipping_email_notifications(
    event,
    prize_winners,
    mail_template,
    domain=settings.DOMAIN,
    sender=None,
    reply_to=None,
    verbosity=0,
    dry_run=False,
):
    sender, reply_to = event_sender_replyto_defaults(event, sender, reply_to)

    winner_dict = {}
    for prize_winner in prize_winners:
        prize_list = winner_dict.setdefault(prize_winner.winner, [])
        prize_list.append(prize_winner)
    for winner, prize_list in winner_dict.items():
        format_context = {
            'prize_wins': prize_list,
            'prize_count': len(prize_list),
            'winner': winner,
            'event': event,
            'reply_address': reply_to,
        }
        if not dry_run:
            post_office.mail.send(
                recipients=[winner.email],
                sender=sender,
                template=mail_template,
                context=format_context,
                headers={'Reply-to': reply_to},
            )
        message = 'Mailed donor {0} for prizes shipped {1}'.format(
            winner.id, list([pw.id for pw in prize_list])
        )
        if verbosity > 0:
            print(message)
        if not dry_run:
            viewutil.tracker_log('prize', message, event)
            for prize_winner in prize_list:
                prize_winner.shippingemailsent = True
                prize_winner.save()
