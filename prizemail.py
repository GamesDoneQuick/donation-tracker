import django.core.mail as mail
from django.db.models import Q
from models import *
import tracker.filters as filters
import smtplib
import settings
import time
import post_office.mail;
from collections import Counter

#TODO: add auto-mail methods for prize submission confirmation as well
# Then, add an admin view to execute both types of prize mailing
# then, update the settings.py on the server to use post_office as well

def prize_winners_with_email_pending(event):
  return PrizeWinner.objects.filter(prize__event=event, emailsent=False)

def automail_prize_winners(event, prizeWinners, mailTemplate, sender=settings.EMAIL_HOST_USER):
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
    }
    print(formatContext)
    post_office.mail.send(recipients=[winner.email], sender=sender, template=mailTemplate.name, context=formatContext)
    for prizeWon in prizesWon:
      prizeWon.emailsent = True
      prizeWon.save()

def estimate_contributor_name(prizes):
  nonEmptyNames = list(sorted(filter(lambda prize: prize.provided, prizes)))
  if len(nonEmptyNames) == 0:
    return None
  counter = Counter()
  for prize in prizes:
    counter[prize.provided] += 1
  return list(reversed(sorted(counter.items(), key=lambda x: x[1])))[0][0]

def prizes_with_submission_email_pending(event):
  return Prize.objects.filter(Q(state='ACCEPTED') | Q(state='DENIED'), acceptemailsent=False, event=event)
      
def automail_prize_contributors(event, prizes, mailTemplate, sender=settings.EMAIL_HOST_USER):
  providerDict = {}
  for prize in prizes:
    if prize.provideremail in providerDict.keys():
      prizeList = providerDict[prize.provideremail]
    else:
      prizeList = []
      providerDict[prize.provideremail] = prizeList
    prizeList.append(prize)
  for providerEmail, prizeList in providerDict.iteritems():
    denied = list(filter(lambda prize: prize.state == 'DENIED', prizeList))
    estimatedName = estimate_contributor_name(prizeList)
    formatContext = {
      'event': event,
      'contributorName': estimatedName if estimatedName != None else providerEmail,
      'acceptedPrizes': list(filter(lambda prize: prize.state == 'ACCEPTED', prizeList)),
      'deniedPrizes': list(filter(lambda prize: prize.state == 'DENIED', prizeList)),
    }
    print(formatContext)
    post_office.mail.send(recipients=[providerEmail], sender=sender, template=mailTemplate.name, context=formatContext)
    for prize in prizeList:
      prize.acceptemailsent = True
      prize.save()