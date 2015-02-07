import csv
import tracker.models as models

def GetAddress(donor):
  addressParts = []
  if donor.addressstreet:
    addressParts.append(donor.addressstreet)
  if donor.addresscity:
    addressParts.append(donor.addresscity)
  if donor.addressstate:
    addressParts.append(donor.addressstate)
  if donor.addresscountry:
    addressParts.append(donor.addresscountry)
  if donor.addresszip:
    addressParts.append(donor.addresszip)
  return '\n'.join(addressParts)

def WritePrizeSheet(event, filename):
  prizes = models.Prize.objects.filter(event=event)
  csvfile = open(filename, 'wb')
  writer = csv.writer(csvfile, delimiter=',', quotechar='"')
  writer.writerow(['Prize', 'Winner', 'Email', 'Address'])
  for prize in prizes:
    for winner in prizes.get_winners():
      writer.writerow([prize.name.encode('utf-8'), (winner.firstname + ' ' + winner.lastname).encode('utf-8'), winner.email.encode('utf-8'), GetAddress(winner).encode('utf-8')])
  csvfile.close()

