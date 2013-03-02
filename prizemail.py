import django.core.mail as mail;
from models import *;
import smtplib;
import settings;
import time;

emailThrottleTime = 20.0
emailFormatText = """Hello %(firstName)s %(lastName)s,

Congratulations, you are the winner of
%(prizesText)s 
during Awesome Games Done Quick 2013, Jan. 6-12.  

If you want your %(prizePlural)s, please reply to this email with %(contactInfo)s if you would like to accept.  If you would like to deny %(anyOfYourPrizes)s please indicate as such in your response. 

The SDA and SRL communities, as well as PCF, thank you very much for your contribution to help make our marathon such a big success, and we hope you will continue to support us in the future.

Sincerely,

Mike Uyama
-speeddemosarchive.com

P.S. If you have trouble responding to my main address, then try mikwuyma@gmail.com.
""";


# Fun fact: django send_mail does not work with SSL
def fixed_send_mail(subject, message, fromAddr, toAddrs):
  msgObj = mail.EmailMessage(subject, message, fromAddr, toAddrs);
  s = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT);
  s.set_debuglevel(1);
  s.connect(settings.EMAIL_HOST, settings.EMAIL_PORT);
  s.ehlo();
  # It seems the SDA server does not allow anything but the plain login method
  # this line must happen _after_ ehlo, since I think it sets the esmtp_features
  s.esmtp_features["auth"] = "LOGIN PLAIN"
  s.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
  s.sendmail(fromAddr, toAddrs, msgObj.message().as_string());

def automail_event(event):
  prizes = Prize.objects.filter(event=event).exclude(winner=None);
  
  winnerDict = {}

  for prize in prizes:
    if not prize.emailsent:
      if prize.winner.id in winnerDict.keys():
        winList = winnerDict[prize.winner.id];
      else:
        winList = [];
        winnerDict[prize.winner.id] = winList;
      winList.append(prize);

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
    cutOffDate = 'February 13th, 2013'; # TODO: get a real date 
    subject = 'AGDQ 2013 Prize';
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
    fixed_send_mail(subject, message, settings.EMAIL_FROM_USER, [winner.email]);  
    time.sleep(emailThrottleTime);
    print(subject + "\n" + message + "\n");
    for prize in winPrizes:
      prize.emailsent = True;
      prize.save();
