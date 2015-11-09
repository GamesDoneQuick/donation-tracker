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
event -- the event object.
winner -- the winner donor object
prizes -- the list of prizes this donor has won
multi -- true if there are multiple prizes, false if there is only one (used for plurality branches)
prizecount -- the number of prizes won
replyaddress -- the reply address specified on the form
""",
        content="""Hello {{ winner.contact_name }},

Congratulations, you were selected as the winner of the following prize{% if multi %}s{% endif %} during {{ event.name }}:

{% for prize in prizes %}- {{ prize.name }}{% if prize.description %}
  Description: {{ prize.description }}{% endif %}
{% endfor %}
If you would like to claim {% if multi %}any of your prizes{% else %}your prize{% endif %} please reply to {{ replyaddress }} by INSERT DATE HERE (if this isn't filled out, please reply telling the person that they didn't modify the e-mail template properly, and that SMK needs to give them a stern talking to about reading instructions).

Once again we would like to thank you for your contribution to helping make our event a success.

Sincerely,
- INSERT CORRESPONDANCE NAME HERE
""")


def automail_prize_winners(event, prizeWinners, mailTemplate, sender=None, replyTo=None):
    if not sender:
        sender = viewutil.get_default_email_host_user()
    if not replyTo:
        replyTo = viewutil.get_default_email_host_user()
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
            'prizeWins': prizesWon,  # this includes the full prizewinner object, which has the list of pending wins. 'prizes' is kept in the dict for backwards compatibility
            'multi': len(prizesList) > 1,
            'prizeCount': len(prizesList),
            'replyaddress': replyTo,
        }
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
        subject='{% if multi %}You won some prizes at {{ event.name }}{% else %}You won a prize at {{ event.name }}{% endif %}',
        description="""A basic template for automailing back prize accept/reject notifications. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
event -- the event object.
contributorName -- the name of the contributor (if provided, falls back to their e-mail).
acceptedPrizes -- A list of all accepted prizes.
deniedPrizes  -- A list of all denied prizes.
""",
        content="""Hello {{ contributorName }},

Thank you for your prize submissions for {{ event.name }}.

{% if acceptedPrizes %}
We are pleased to let you know that the following prize(s) have been accepted for the event:
{% for prize in acceptedPrizes %}
  {{ prize.name }}
{% endfor %}

{% endif %}
{% if deniedPrizes %}
Unfortunately, we were unable to accept the following prize(s):
{% for prize in deniedPrizes %}
  {{ prize.name }}
{% endfor %}

{% endif %}
If you have any questions, please notify the staff using the reply e-mail specified.

Sincerely,
- The GamesDoneQuick staff
""")


def automail_prize_contributors(event, prizes, mailTemplate, sender=None, replyTo=None):
    if not sender:
        sender = viewutil.get_default_email_host_user()
    if not replyTo:
        replyTo = viewutil.get_default_email_host_user()
    providerDict = {}
    for prize in prizes:
        if prize.provider:
            prizeList = providerDict.setdefault(prize.provider, [])
            prizeList.append(prize)
    for provider, prizeList in providerDict.iteritems():
        denied = list(filter(lambda prize: prize.state == 'DENIED', prizeList))
        formatContext = {
            'event': event,
            'contributorName': provider.username,
            'acceptedPrizes': list(filter(lambda prize: prize.state == 'ACCEPTED', prizeList)),
            'deniedPrizes': list(filter(lambda prize: prize.state == 'DENIED', prizeList)),
        }
        post_office.mail.send(recipients=[provider.email], sender=sender,
                              template=mailTemplate.name, context=formatContext, headers={'Reply-to': replyTo})
        for prize in prizeList:
            prize.acceptemailsent = True
            prize.save()


def prizes_with_winner_accept_email_pending(event):
    return Prize.objects.filter(Q(state='ACCEPTED') & Q(acceptcount__lte=F('acceptemailsentcount')))


def default_prize_winner_accept_template_name():
    return getattr(settings, 'WINNER_ACCEPT_EMAIL_TEMPLATE_NAME', 'default_prize_winner_accept_template')


def default_prize_winner_accept_template():
    return post_office.models.EmailTemplate(
        name=default_prize_winner_accept_template_name(), 
        description="""A basic template for automailing when prizes are accepted by winners. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
user_index_url -- the user index url (i.e. /user/index)
prizeList -- the list of prizes that were accepted
prizeCount -- the number of prizes in the list
provider  -- the user that contributed the prizes
""",
        subject='Prize{{ prizeCount|pluralize }} Accepted',
        content="""Hello {{ provider }},
    {% if prizeCount > 1 %}Some prize winners have accepted your prizes.{% else %}A prize winner has accepted your prize.{% endif %}
    
    Please view the list of prizes to be shipped here: {{ user_index_url }}

    - The Staff
""")


def automail_winner_accepted_prize(event, prizeWinners, mailTemplate, domain=settings.DOMAIN, sender=None, replyTo=None):
    if not sender:
        sender = viewutil.get_default_email_host_user()
    if not replyTo:
        replyTo = viewutil.get_default_email_host_user()
    providerDict = {}
    for prizeWinner in prizeWinners:
        if prizeWinner.provider:
            prizeList = providerDict.setdefault(prizeWinner.prize.provider, [])
            prizeList.append(prizeWinner)
    for provider, prizeList in providerDict.iteritems():
        formatContext = {
            'user_index_url': domain + reverse('user_index'),
            'prizeList': prizeList,
            'prizeCount': len(prizeList),
            'provider': provider,
        }
        post_office.mail.send(recipients=[provider.email], sender=sender,
            template=mailTemplate, context=formatContext, headers={'Reply-to': replyTo})
        for prizeWinner in prizeList:
            prizeWinner.acceptemailsentcount = prizeWinner.acceptcount
            prizeWinner.save()


def prizes_with_shipping_email_pending(event):
    return Prize.objects.filter(Q(shippingstate='SHIPPED') & Q(shippingemailsent=False))


def default_prize_shipping_template_name():
    return getattr(settings, 'SHIPPING_EMAIL_TEMPLATE_NAME', 'default_prize_shipping_template')


def default_prize_shipping_template():
    return post_office.models.EmailTemplate(
        name=default_prize_shipping_template_name(), 
        description="""A basic template for automailing when prizes are shipped. DO NOT USE THIS TEMPLATE. Copy the contents and modify it to suit your needs.

The variables that will be defined are:
user_index_url -- the user index url (i.e. /user/index)
prizeList -- the list of prizes that were accepted
prizeCount -- the number of prizes in the list
provider  -- the user that contributed the prizes
""",
        subject='Prize{{ prizeCount|pluralize }} Shipped',
        content="""Hello {{ winner }},
    {% if prizeCount > 1 %}Your prizes have been shipped{% else %}Your prize has been shipped{% endif %}
    
    Please view the list of prizes to be shipped here: {{ user_index_url }}

    - The Staff
""")


def automail_shipping_email_notifications(event, prizeWinners, mailTemplate, domain=settings.DOMAIN, sender=None, replyTo=None):
    if not sender:
        sender = viewutil.get_default_email_host_user()
    if not replyTo:
        replyTo = viewutil.get_default_email_host_user()
    providerDict = {}
    for prizeWinner in prizeWinners:
        if prizeWinner.provider:
            prizeList = providerDict.setdefault(prizeWinner.prize.provider, [])
            prizeList.append(prizeWinner)
    for provider, prizeList in providerDict.iteritems():
        formatContext = {
            'user_index_url': domain + reverse('user_index'),
            'prizeList': prizeList,
            'prizeCount': len(prizeList),
            'provider': provider,
        }
        post_office.mail.send(recipients=[provider.email], sender=sender,
            template=mailTemplate, context=formatContext, headers={'Reply-to': replyTo})
        for prizeWinner in prizeList:
            prizeWinner.acceptemailsentcount = prizeWinner.acceptcount
            prizeWinner.save()

