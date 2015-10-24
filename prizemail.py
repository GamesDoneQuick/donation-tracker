import django.core.mail as mail
from django.db.models import Q
from models import *
import tracker.filters as filters
import tracker.viewutil as viewutil
import smtplib
import settings
import post_office.mail
from collections import Counter


def prize_winners_with_email_pending(event):
    return PrizeWinner.objects.filter(prize__event=event, pendingcount__gt=0, emailsent=False)


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
            'replyaddress': replyTo,
        }
        post_office.mail.send(recipients=[winner.email], sender=sender,
                              template=mailTemplate.name, context=formatContext, headers={'Reply-to': replyTo})
        for prizeWon in prizesWon:
            prizeWon.emailsent = True
            prizeWon.save()

def prizes_with_submission_email_pending(event):
    return Prize.objects.filter(Q(state='ACCEPTED') | Q(state='DENIED'), acceptemailsent=False, event=event)


def automail_prize_contributors(event, prizes, mailTemplate, sender=None, replyTo=None):
    if not sender:
        sender = viewutil.get_default_email_host_user()
    if not replyTo:
        replyTo = viewutil.get_default_email_host_user()
    providerDict = {}
    for prize in prizes:
        if prize.provider:
            if prize.provider in providerDict.keys():
                prizeList = providerDict[prize.provider]
            else:
                prizeList = []
                providerDict[prize.provider] = prizeList
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
