import django.core.mail as mail;
from models import *;
import smtplib;
import settings;

emailFormatText = """Hello %(firstName)s %(lastName)s,

Congratulations, you were selected as the winner of 
%(prizesText)s 
during Awesome Games Done Quick 2013, Jan. 6-12.  

If you want your %(prizePlural)s, please reply to this email with %(contactInfo)s if you would like to accept.  If you would like to deny %(anyOfYourPrizes)s please indicate as such in your response.  We will reroll %(allOfYourPrizes)s if we do not receive any reponse by %(cutOffDate)s.

Sincierely,
- The organizers of AGDQ 2013""";

def _fixed_send_mail(subject, message, fromAddr, toAddrs):
  msgObj = mail.EmailMessage(subject, message, fromAddr, toAddrs);
  s = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT);
  s.connect(settings.EMAIL_HOST, settings.EMAIL_PORT);
  s.verify();
  s.esmtp_features["auth"] = "LOGIN PLAIN"
  s.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
  s.sendmail(fromAddr, toAddrs, msgObj.message().as_string());

def automail_event(event):
  prizes = Prize.objects.filter(event=event).exclude(winner=None);
  
  winnerDict = {}

  for prize in prizes:
    if prize.winner.id in winnerDict.keys():
      winList = winnerDict[prize.winner.id];
    else:
      winList = [];
      winnerDict[prize.winner.id] = winList;
    winList.append(prize);

  tries = 0;

  for winnerk in winnerDict:
    winPrizes = winnerDict[winnerk];
    winner = winPrizes[0].winner;
    multi = len(winPrizes) > 1;
    firstName = winner.firstname;
    lastName = winner.lastname;
    prizePlural = 'prizes' if multi else 'prize';
    prizesList = [];
    steam = False;
    realAddress = False;
    for prize in winPrizes:
      curSteam = False if prize.name.lower().find('steam') == -1 else True;
      steam = steam or curSteam;
      realAddress = realAddress or not curSteam;
      prizeText = '- ' + prize.name;
      if len(prize.description.strip()) > 0:
        prizeText += "\n\t(Notes: " + prize.description + ")";
      prizesList.append(prizeText);
    prizesText = '\n\n'.join(prizesList);
    contactList = [];
    if realAddress:
      contactList.append("your mailing address (yes, we do ship internationally)");
    if steam:
      contactList.append("your steamid");
    if len(contactList) > 1:
      contactList[-1] = "and " + contactList[-1];
    contactInfo = ', '.join(contactList);
    anyOfYourPrizes = 'any of your prizes' if multi else 'your prize';
    allOfYourPrizes = 'all of your prizes' if multi else 'your prize';
    prizePlural = 'prizes' if multi else 'prize';
    cutOffDate = 'February 29th, 2013'; # TODO: get a real date 
    subject = 'Prize Winner for AGDQ 2013';
    formatSet = {
      'firstName': firstName,
      'lastName': lastName,
      'prizesText': prizesText,
      'contactInfo': contactInfo,
      'anyOfYourPrizes': anyOfYourPrizes,
      'allOfYourPrizes': allOfYourPrizes,
      'prizePlural': prizePlural,
      'cutOffDate': cutOffDate }; 
    message = emailFormatText % formatSet;
    if tries < 3:
      tries += 1;
      print(subject + "\n" + message + "\n");
    
