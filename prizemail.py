import django.core.mail as mail
from models import *
import tracker.filters as filters
import smtplib
import settings
import time

emailThrottleTime = 1.0

# Fun fact: django send_mail does not work with SSL
def fixed_send_mail(subject, message, fromAddr, toAddrs):
  msgObj = mail.EmailMessage(subject, message, fromAddr, toAddrs)
  s = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
  s.set_debuglevel(1)
  s.connect(settings.EMAIL_HOST, settings.EMAIL_PORT)
  s.ehlo()
  # It seems the SDA server does not allow anything but the plain login method
  # this line must happen _after_ ehlo, since I think it sets the esmtp_features
  s.esmtp_features["auth"] = "LOGIN PLAIN"
  s.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
  s.sendmail(fromAddr, toAddrs, msgObj.message().as_string())

def automail_event(event):
  prizes = Prize.objects.filter(event=event).exclude(winners__isnull=True)
  
  winnerDict = {}

  for prize in prizes:
    for prizeWinner in prize.prizewinner_set.all():
      if not prizeWinner.emailsent:
        if prizeWinner.winner.id in winnerDict.keys():
          winList = winnerDict[prizeWinner.winner.id]
        else:
          winList = []
          winnerDict[prizeWinner.winner.id] = winList
        winList.append(prizeWinner)

  for winnerk in winnerDict:
    prizesWon = winnerDict[winnerk]
    winner = prizesWon[0].winner
    multi = len(prizesWon) > 1
    prizePlural = 'prizes' if multi else 'prize'
    prizesList = []
    steam = False
    realAddress = False
    for prizeWon in prizesWon:
      prize = prizeWon.prize
      curSteam = False if prize.name.lower().find('steam') == -1 else True
      steam = steam or curSteam
      realAddress = realAddress or not curSteam
      prizeText = '- ' + prize.name
      if len(prize.description.strip()) > 0:
        prizeText += "\n\t(Notes: " + prize.description + ")"
      prizesList.append(prizeText)
    prizesText = '\n\n'.join(prizesList)
    contactList = []
    if realAddress:
      contactList.append("your mailing address (yes, we do ship internationally)")
    if steam:
      contactList.append("your steamid")
    if len(contactList) > 1:
      contactList[-1] = "and " + contactList[-1]
    contactInfo = ', '.join(contactList)
    anyOfYourPrizes = 'any of your prizes' if multi else 'your prize'
    allOfYourPrizes = 'all of your prizes' if multi else 'your prize'
    prizePlural = 'prizes' if multi else 'prize'
    formatSet = {
      'eventname': event.name,
      'eventshort': event.short,
      'firstname': winner.firstname,
      'lastname': winner.lastname,
      'alias': winner.alias,
      'visiblename': winner.visible_name(),
      'prizestext': prizesText,
      'contactinfo': contactInfo,
      'anyofyourprizes': anyOfYourPrizes,
      'allofyourprizes': allOfYourPrizes,
      'prizeplural': prizePlural,
    }
    print(formatSet)
    subject = event.prizemailsubject.format(**formatSet)
    message = event.prizemailbody.format(**formatSet)
    fixed_send_mail(subject, message, settings.EMAIL_FROM_USER, [winner.email])
    for prizeWon in prizesWon:
      prizeWon.emailsent = True
      prizeWon.save()
    time.sleep(emailThrottleTime)

