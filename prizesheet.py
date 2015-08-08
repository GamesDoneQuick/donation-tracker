import csv
import tracker.models as models

def GetAddress(donor):
  parts = [getattr(donor, 'address' + part, '') for part in ['street', 'city', 'state', 'country', 'zip']]
  return '\n'.join(filter(None, parts))

def WritePrizeSheet(event, filename):
  prizes = models.Prize.objects.filter(event=event)
  csvfile = open(filename, 'wb')
  writer = csv.writer(csvfile, delimiter=',', quotechar='"')
  writer.writerow(['Prize', 'Winner', 'Email', 'Address'])
  for prize in prizes:
    for winner in prizes.get_winners():
      writer.writerow([prize.name.encode('utf-8'), (winner.firstname + ' ' + winner.lastname).encode('utf-8'), winner.email.encode('utf-8'), GetAddress(winner).encode('utf-8')])
  csvfile.close()

