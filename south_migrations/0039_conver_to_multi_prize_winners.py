# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models
from django.db.models import Q

class Migration(DataMigration):
  def forwards(self, orm):
    "Write your forwards methods here."
    "NOTE: this will only set the prize winner if no winners have already been set (i.e. don't touch the db in between the previous and next migration)."
    # Note: Remember to use orm['appname.ModelName'] rather than "from appname.models..."
    for prize in orm['tracker.Prize'].objects.filter(winner__isnull=False, winners=None):
      created = orm['tracker.PrizeWinner'].objects.create(winner=prize.winner, prize=prize, emailsent=prize.emailsent)
      prize.winner = None
      created.save()
      prize.save()

  def backwards(self, orm):
    "Write your backwards methods here."
    for prize in orm['tracker.Prize'].objects.filter(~Q(winners=None)):
      prizeWinnerRec = prize.prizewinner_set.all()[0]
      prize.winner = prizeWinnerRec.winner
      prize.emailsent = prizeWinnerRec.emailsent
      prize.winners.clear()
      prize.save()

  models = {
      u'auth.group': {
          'Meta': {'object_name': 'Group'},
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
          'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
      },
      u'auth.permission': {
          'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
          'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
          'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
      },
      u'auth.user': {
          'Meta': {'object_name': 'User'},
          'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
          'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
          'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
          'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
          'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
          'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
          'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
          'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
          'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
          'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
          'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
      },
      u'contenttypes.contenttype': {
          'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
          'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
          'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
      },
      u'tracker.bid': {
          'Meta': {'ordering': "['event__name', 'speedrun__starttime', 'parent__name', 'name']", 'unique_together': "(('event', 'name', 'speedrun', 'parent'),)", 'object_name': 'Bid'},
          'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'blank': 'True'}),
          'event': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'bids'", 'null': 'True', 'to': u"orm['tracker.Event']"}),
          'goal': ('django.db.models.fields.DecimalField', [], {'default': 'None', 'null': 'True', 'max_digits': '20', 'decimal_places': '2', 'blank': 'True'}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'istarget': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
          u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
          u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
          'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
          'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'options'", 'null': 'True', 'to': u"orm['tracker.Bid']"}),
          'revealedtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
          u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
          'speedrun': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'bids'", 'null': 'True', 'to': u"orm['tracker.SpeedRun']"}),
          'state': ('django.db.models.fields.CharField', [], {'default': "'OPENED'", 'max_length': '32'}),
          u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
      },
      u'tracker.bidsuggestion': {
          'Meta': {'ordering': "['name']", 'object_name': 'BidSuggestion'},
          'bid': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'suggestions'", 'to': u"orm['tracker.Bid']"}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
      },
      u'tracker.donation': {
          'Meta': {'ordering': "['-timereceived']", 'object_name': 'Donation'},
          'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
          'bidstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '255'}),
          'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
          'commentlanguage': ('django.db.models.fields.CharField', [], {'default': "'un'", 'max_length': '32'}),
          'commentstate': ('django.db.models.fields.CharField', [], {'default': "'ABSENT'", 'max_length': '255'}),
          'currency': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
          'domain': ('django.db.models.fields.CharField', [], {'default': "'LOCAL'", 'max_length': '255'}),
          'domainId': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '160', 'blank': 'True'}),
          'donor': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tracker.Donor']", 'null': 'True', 'blank': 'True'}),
          'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tracker.Event']"}),
          'fee': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '20', 'decimal_places': '2'}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'modcomment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
          'readstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '255'}),
          'requestedalias': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
          'requestedemail': ('django.db.models.fields.EmailField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
          'requestedvisibility': ('django.db.models.fields.CharField', [], {'default': "'CURR'", 'max_length': '32'}),
          'testdonation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
          'timereceived': ('django.db.models.fields.DateTimeField', [], {}),
          'transactionstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '64'})
      },
      u'tracker.donationbid': {
          'Meta': {'ordering': "['-donation__timereceived']", 'object_name': 'DonationBid'},
          'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
          'bid': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bids'", 'to': u"orm['tracker.Bid']"}),
          'donation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bids'", 'to': u"orm['tracker.Donation']"}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
      },
      u'tracker.donor': {
          'Meta': {'ordering': "['lastname', 'firstname', 'email']", 'object_name': 'Donor'},
          'addresscity': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'addresscountry': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'addressstate': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'addressstreet': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'addresszip': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'alias': ('django.db.models.fields.CharField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
          'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '128'}),
          'firstname': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'lastname': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
          'paypalemail': ('django.db.models.fields.EmailField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
          'prizecontributoremail': ('django.db.models.fields.EmailField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
          'prizecontributorwebsite': ('django.db.models.fields.URLField', [], {'max_length': '200', 'null': 'True', 'blank': 'True'}),
          'runnertwitch': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
          'runnertwitter': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
          'runneryoutube': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
          'visibility': ('django.db.models.fields.CharField', [], {'default': "'FIRST'", 'max_length': '32'})
      },
      u'tracker.event': {
          'Meta': {'object_name': 'Event'},
          'date': ('django.db.models.fields.DateField', [], {}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
          'paypalcurrency': ('django.db.models.fields.CharField', [], {'default': "'USD'", 'max_length': '8'}),
          'paypalemail': ('django.db.models.fields.EmailField', [], {'max_length': '128'}),
          'receivername': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'schedulecommentatorsfield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'schedulecommentsfield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'scheduledatetimefield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'scheduleestimatefield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'schedulegamefield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'scheduleid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
          'schedulerunnersfield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'schedulesetupfield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
          'scheduletimezone': ('django.db.models.fields.CharField', [], {'default': "'US/Eastern'", 'max_length': '64', 'blank': 'True'}),
          'short': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
          'targetamount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
          'usepaypalsandbox': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
      },
      u'tracker.prize': {
          'Meta': {'ordering': "['event__date', 'startrun__starttime', 'starttime', 'name']", 'unique_together': "(('category', 'winner', 'event'),)", 'object_name': 'Prize'},
          'category': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tracker.PrizeCategory']", 'null': 'True', 'blank': 'True'}),
          'contributors': ('django.db.models.fields.related.ManyToManyField', [], {'blank': 'True', 'related_name': "'prizescontributed'", 'null': 'True', 'symmetrical': 'False', 'to': u"orm['tracker.Donor']"}),
          'deprecated_provided': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
          'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
          'emailsent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
          'endrun': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prize_end'", 'null': 'True', 'to': u"orm['tracker.SpeedRun']"}),
          'endtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
          'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tracker.Event']"}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'image': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
          'maximumbid': ('django.db.models.fields.DecimalField', [], {'default': "'5.0'", 'null': 'True', 'max_digits': '20', 'decimal_places': '2', 'blank': 'True'}),
          'maxwinners': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
          'minimumbid': ('django.db.models.fields.DecimalField', [], {'default': "'5.0'", 'max_digits': '20', 'decimal_places': '2'}),
          'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
          'randomdraw': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
          'sortkey': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
          'startrun': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prize_start'", 'null': 'True', 'to': u"orm['tracker.SpeedRun']"}),
          'starttime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
          'sumdonations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
          'ticketdraw': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
          'winner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tracker.Donor']", 'null': 'True', 'blank': 'True'}),
          'winners': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'prizeswon'", 'to': u"orm['tracker.Donor']", 'through': u"orm['tracker.PrizeWinner']", 'blank': 'True', 'symmetrical': 'False', 'null': 'True'})
      },
      u'tracker.prizecategory': {
          'Meta': {'object_name': 'PrizeCategory'},
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
      },
      u'tracker.prizeticket': {
          'Meta': {'ordering': "['-donation__timereceived']", 'object_name': 'PrizeTicket'},
          'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
          'donation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tickets'", 'to': u"orm['tracker.Donation']"}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'prize': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tickets'", 'to': u"orm['tracker.Prize']"})
      },
      u'tracker.prizewinner': {
          'Meta': {'unique_together': "(('prize', 'winner'),)", 'object_name': 'PrizeWinner'},
          'emailsent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'prize': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tracker.Prize']"}),
          'winner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tracker.Donor']"})
      },
      u'tracker.speedrun': {
          'Meta': {'ordering': "['event__date', 'starttime']", 'unique_together': "(('name', 'event'),)", 'object_name': 'SpeedRun'},
          'deprecated_runners': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
          'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'blank': 'True'}),
          'endtime': ('django.db.models.fields.DateTimeField', [], {}),
          'event': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['tracker.Event']"}),
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
          'runners': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': u"orm['tracker.Donor']", 'null': 'True', 'blank': 'True'}),
          'sortkey': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
          'starttime': ('django.db.models.fields.DateTimeField', [], {})
      },
      u'tracker.userprofile': {
          'Meta': {'object_name': 'UserProfile'},
          u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
          'prepend': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
          'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'unique': 'True'})
      }
  }

  complete_apps = ['tracker']
  symmetrical = True
