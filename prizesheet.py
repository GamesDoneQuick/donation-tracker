import csv;
import tracker.models as models;

def GetAddress(donor):
  return '\n'.join([donor.addressstreet, donor.addresscity, donor.addressstate, donor.addresscountry, donor.addresszip]);

def WritePrizeSheet(event, filename):
  prizes = models.Prize.objects.filter(event=event);
  csvfile = open(filename, 'wb');
  writer = csv.writer(csvfile, delimiter=',', quotechar='"');
  writer.writerow(['Prize', 'Winner', 'Email', 'Address']);
  for prize in prizes:
    writer.writerow([prize.name, prize.winner.firstname + ' ' + prize.winner.lastname, prize.winner.contactemail, GetAddress(prize.winner)]);
  csvfile.close();

