from collections import Counter
import smtplib

import django.core.mail as mail
from django.db.models import Q, F
from django.core.urlresolvers import reverse

import post_office.mail

import settings

from tracker.models import *
import tracker.filters as filters
import tracker.viewutil as viewutil

def get_event_default_sender_email(event):
    if event and event.prizecoordinator:
        sender = event.prizecoordinator.email
    else:
        sender = viewutil.get_default_email_host_user()

def event_sender_replyto_defaults(event, sender=None, replyTo=None):
    sender = sender or get_event_default_sender_email(event)
    replyTo = replyTo or sender
    return sender, replyTo
        
def prize_winners_with_email_pending(event):
    return PrizeWinner.objects.filter(prize__event=event, pendingcount__gt=0, emailsent=False)


def default_prize_winner_template_name():
    return getattr(settings, 'PRIZE_WINNER_EMAIL_TEMPLATE_NAME', 'default_prize_winner_template')


def default_prize_winner_template():
    return post_office.models.EmailTemplate(
        name=default_prize_winner_template_name(), 
        subject='{% if multi %}You won some prizes at {{ event.name }}{% else %}You won a prize at {{ event.name }}{% endif %}',
        description="""A basic template for automailing prize winners. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
event -- the event for the set of prizes
winner -- the winner donor object
prizes -- the list of prizes this donor has won
prize_wins -- the list of PrizeWinner objects for this donor (if you need the additional information)
multi -- true if there are multiple prizes, false if there is only one (used for plurality branches)
prize_count -- the number of prizes won
reply_address -- the reply address specified on the form (will be overridden if the event has a prize coordinator)
user_index_url -- the user index page   1   
registration_link -- the page for user registration
password_reset_link -- the page for password reset
""",
        html_content="""Hello {{ winner.contact_name }},

    <p>
    Congratulations, you were selected as the winner of the following prize{% if multi %}s{% endif %} during {{ event.name }}:
    <ul>
{% for prize in prizes %}
    <li>{{ prize.name }}
    {% if prize.description %}
        <p>
        Description: {{ prize.description }}
        </p>
    {% endif %} 
    </li>
{% endfor %}
    </p>
    
    <p>
    If you would like to claim {% if multi %}any of your prizes{% else %}your prize{% endif %} please 
    {% if not winner.user or not winner.user.is_active %}
        register your e-mail for an account <a href="{{ registration_link }}">here</a> (note: you <b>must</b> use {{ winner.user.email }} for this to work correctly). Once you've registered, you can
    {% endif %}
    view your user page <a href="{{ user_index_url }}">here</a> (will require log-in) and accept/deny your prize{{ prize_count|pluralize }} using the link{{ prize_count|pluralize }} on that page.
    {% if winner.user and winner.user.is_active %}
    If you forgot your password (or don't remember setting it in the first place), you can re-set it using the link <a href="{{ password_reset_link }}">here</a>.
    {% endif %}
    </p>
    
    <p>
    You will also be asked to fill in your mailing address information (we may already have it on file from a previous event, in which case, simply confirm that the information is correct.
    </p>
    
    <p>
    You must accept/deny your prize by INSERT DATE HERE (if this isn't filled out, please reply telling the person that they didn't modify the e-mail template properly, 
    and that SMK needs to give them a stern talking to about reading instructions), otherwise it will be automatically re-rolled. Even if you want to decline receiving your prize however,
    we would ask you do so promptly so we can proceed with prize shipping efficiently.
    </p>
    
    <p> 
    If you have any questions, please contact me at {{ reply_address }}. 
    </p>
    
    <p>
    Once again we would like to thank you for your contribution in helping to make our event a success.
    </p>

Sincerely,
- INSERT CORRESPONDANCE NAME HERE
""")


def automail_prize_winners(event, prizeWinners, mailTemplate, sender=None, replyTo=None, domain=settings.DOMAIN):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)
    
    winnerDict = {}
    for prizeWinner in prizeWinners:
        if prizeWinner.winner.id in winnerDict.keys():
            winList = winnerDict[prizeWinner.winner.id]
        else:
            winList = []
            winnerDict[prizeWinner.winner.id] = winList
        winList.append(prizeWinner)
    for winnerk, prizesWon in winnerDict.iteritems():
        winner = prizesWon[0].winner
        prizesList = []
        for prizeWon in prizesWon:
            prizesList.append(prizeWon.prize)
        formatContext = {
            'event': event,
            'winner': winner,
            'prizes': prizesList,
            'prize_wins': prizesWon,  # this includes the full prizewinner object, which has the list of pending wins. 'prizes' is kept in the dict for backwards compatibility
            'multi': len(prizesList) > 1,
            'prize_count': len(prizesList),
            'reply_address': replyTo,
            'user_index_url': domain + reverse('user_index'),
            'registration_link': domain + reverse('register'),
            'password_reset_link': domain + reverse('password_reset'),
        }
        # ensure this donor has a linked user object
        viewutil.autocreate_donor_user(winner)
        post_office.mail.send(recipients=[winner.email], sender=sender,
                              template=mailTemplate.name, context=formatContext, headers={'Reply-to': replyTo})
        for prizeWon in prizesWon:
            prizeWon.emailsent = True
            prizeWon.save()


def prizes_with_submission_email_pending(event):
    return Prize.objects.filter(Q(state='ACCEPTED') | Q(state='DENIED'), acceptemailsent=False, event=event)


def default_prize_contributor_template_name():
    return getattr(settings, 'PRIZE_WINNER_EMAIL_TEMPLATE_NAME', 'default_prize_contributor_template')


def default_prize_contributor_template():
    return post_office.models.EmailTemplate(
        name=default_prize_contributor_template_name(), 
        subject='{{ event.name }} Prize Contributor Notification',
        description="""A basic template for automailing back prize accept/reject notifications. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
event -- the event object.
provider_name -- the name of the contributor (if provided, falls back to their e-mail).
provider -- the provider User object
accepted_prizes -- A list of all accepted prizes.
denied_prizes  -- A list of all denied prizes.
reply_address -- The address to reply to on this e-mail
user_index_url -- the user index url (i.e. /user/index)
event -- the event for the set of prizes
""",
        html_content="""Hello {{ provider_name }},

    <p>
    Thank you for your prize submissiom for {{ event.name }}.
    </p>

    {% if accepted_prizes %}
    <p>
    We are pleased to let you know that the following prize(s) have been accepted for the event:
    <ul>
    {% for prize in accepted_prizes %}
        <li>{{ prize.name }}</li>
    {% endfor %}
    </ul>

    To view the status of these prizes, please follow this link: {{user_index_url}} (note: you may need to log in first).
    </p>
    {% endif %}

    {% if denied_prizes %}
    <p>
        Unfortunately, we were unable to accept the following prize(s):
        <ul>
        {% for prize in denied_prizes %}
            <li>{{ prize.name }}</li>
        {% endfor %}
        </ul>
    </p>
    {% endif %}

    {% if accepted_prizes %}
    On behalf of the entire GamesDoneQuick staff, thank you for your generosity in support of our event.
    {% endif %}
    
    <p> 
    If you have any questions, please contact me at {{ reply_address }}. 
    </p>

    - The GamesDoneQuick staff
""")


def automail_prize_contributors(event, prizes, mailTemplate, domain=settings.DOMAIN, sender=None, replyTo=None):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)
    
    providerDict = {}
    for prize in prizes:
        if prize.provider:
            prizeList = providerDict.setdefault(prize.provider, [])
            prizeList.append(prize)
    for provider, prizeList in providerDict.iteritems():
        denied = list(filter(lambda prize: prize.state == 'DENIED', prizeList))
        formatContext = {
            'user_index_url': domain + reverse('user_index'),
            'event': event,
            'provider_name': provider.username,
            'provider': provider,
            'accepted_prizes': list(filter(lambda prize: prize.state == 'ACCEPTED', prizeList)),
            'denied_prizes': list(filter(lambda prize: prize.state == 'DENIED', prizeList)),
            'reply_address': replyTo,
            'event': event,
        }
        post_office.mail.send(recipients=[provider.email], sender=sender,
                              template=mailTemplate.name, context=formatContext, headers={'Reply-to': replyTo})
        for prize in prizeList:
            prize.acceptemailsent = True
            prize.save()


def prizes_with_winner_accept_email_pending(event):
    return PrizeWinner.objects.filter(Q(prize__state='ACCEPTED') & Q(acceptcount__gt=F('acceptemailsentcount')))


def default_prize_winner_accept_template_name():
    return getattr(settings, 'WINNER_ACCEPT_EMAIL_TEMPLATE_NAME', 'default_prize_winner_accept_template')


def default_prize_winner_accept_template():
    return post_office.models.EmailTemplate(
        name=default_prize_winner_accept_template_name(), 
        description="""A basic template for automailing when prizes are accepted by winners. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
user_index_url -- the user index url (i.e. /user/index)
prize_wins -- the list of PrizeWinner objects that were accepted
prize_count -- the number of prizes in the list
provider  -- the user that contributed the prizes
event -- the event for the set of prizes
reply_address -- the address to reply to (will be overridden if the event has a prize coordinator)
""",
        subject='Your Prize{{ prize_count|pluralize }} {{ prize_count|pluralize:"Has:Have" }} Been Accepted',
        html_content="""Hello {{ provider }},
            
    <p>
    {% if prize_count > 1 %}Some prize winners have accepted your prizes.{% else %}A prize winner has accepted your prize.{% endif %}

    <ul>
    {% for prizeWin in prize_wins %}
        <li>{{ prizeWin.prize }} for {{ prizeWin.winner.visible_name }}
        {% if prizeWin.winnernotes %}
            <p>
            Winner's Notes: {{ prizeWin.winnernotes }}
            </p>
        {% endif %}
        </li>
    {% endfor %}
    </ul>
    </p>
    
    <p>
    You can view the list of prizes to be shipped, as well as the mailing address details <a href="{{ user_index_url }}">here</a> (The prizes which are ready to be shipped will be marked "pending shipping").
    </p>
    
    <p>
    Please ship at your earlest convenience, and mark the prizes as 'shipped' on the site when you do.
    </p>
    
    <p> 
    If you have any questions, please contact me at {{ reply_address }}.
    </p>
    
    - The GamesDoneQuick Staff
""")    


def automail_winner_accepted_prize(event, prizeWinners, mailTemplate, domain=settings.DOMAIN, sender=None, replyTo=None):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)
    
    providerDict = {}
    for prizeWinner in prizeWinners:
        if prizeWinner.prize.provider:
            prizeList = providerDict.setdefault(prizeWinner.prize.provider, [])
            prizeList.append(prizeWinner)
    for provider, prizeList in providerDict.iteritems():
        formatContext = {
            'user_index_url': domain + reverse('user_index'),
            'prize_wins': prizeList,
            'prize_count': len(prizeList),
            'provider': provider,
            'event': event,
        }
        post_office.mail.send(recipients=[provider.email], sender=sender,
            template=mailTemplate, context=formatContext, headers={'Reply-to': replyTo})
        for prizeWinner in prizeList:
            prizeWinner.acceptemailsentcount = prizeWinner.acceptcount
            prizeWinner.save()


def prizes_with_shipping_email_pending(event):
    return PrizeWinner.objects.filter(Q(shippingstate='SHIPPED') & Q(shippingemailsent=False))


def default_prize_shipping_template_name():
    return getattr(settings, 'SHIPPING_EMAIL_TEMPLATE_NAME', 'default_prize_shipping_template')


def default_prize_shipping_template():
    return post_office.models.EmailTemplate(
        name=default_prize_shipping_template_name(), 
        description="""A basic template for automailing when prizes are shipped. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
user_index_url -- the user index url (i.e. /user/index)
prize_wins -- the list PrizeWinner objects
prize_count -- the number of prizes in the list
winner -- the donor that won the prizes
event -- the event for the set of prizes
reply_address -- the address to reply to (will be overridden if the event has a prize coordinator)
""",
        subject='Prize{{ prizeCount|pluralize }} Shipped',
        html_content="""Hello {{ winner }},
    <p>
    The following prize{{ prize_count|pluralize }} {{ prize_count|pluralize:"has,have" }} been shipped to you:
    </p>
    
    <ul>
    {% for prizeWin in prize_wins %}
        <li> {{ prizeWin.prize }}
          {% if prizeWin.couriername %}<p><b>Courier:</b> {{ prizeWin.couriername }}</p>{% if prizeWin.trackingnumber %}<p><b>Tracking#:</b> {{prizeWin.trackingnumber}}</p>{% endif %}{% endif %}
          {% if prizeWin.shippingnotes %}<p><b>Shipping Notes:</b> {{ prizeWin.shippingnotes }}</p>{% endif %}
        </li>
    {% endfor %}
    </ul>
    
    <p>
    As always, you can view the status of your prize{{ prize_count|pluralize }} here: {{ user_index_url }}
    </p>

    <p> 
    If you have any questions, please contact me at {{ reply_address }}.
    </p>
    
    - The GamesDoneQuick Staff
""")


def automail_shipping_email_notifications(event, prizeWinners, mailTemplate, domain=settings.DOMAIN, sender=None, replyTo=None):
    sender, replyTo = event_sender_replyto_defaults(event, sender, replyTo)
    
    winnerDict = {}
    for prizeWinner in prizeWinners:
        prizeList = winnerDict.setdefault(prizeWinner.winner, [])
        prizeList.append(prizeWinner)
    for winner, prizeList in winnerDict.iteritems():
        formatContext = {
            'user_index_url': domain + reverse('user_index'),
            'prize_wins': prizeList,
            'prize_count': len(prizeList),
            'winner': winner,
            'event': event,
            'reply_address': replyTo,
        }
        post_office.mail.send(recipients=[winner.email], sender=sender,
            template=mailTemplate, context=formatContext, headers={'Reply-to': replyTo})
        for prizeWinner in prizeList:
            prizeWinner.acceptemailsentcount = prizeWinner.acceptcount
            prizeWinner.save()

