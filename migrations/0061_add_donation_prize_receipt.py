# -*- coding: utf-8 -*-
from south.utils import datetime_utils as datetime
from south.db import db
from south.v2 import DataMigration
from django.db import models

defaultName = "default_donation_receipt_template_with_prizes"

description = """
This is a more involved template for donation receipt notification, which includes prize information. Once again, DO NOT USE THIS TEMPLATE. It is meant to serve as, well, a template. Copy it out, and modify it to suit the particular needs of your event.

The variables that will be defined are:
event -- the event object
donation -- the donation object
donor -- the donation object
prizes -- a list of {'prize','amount'} dictionaries, detailing the contribution amounts for the current donation.

Using the last one might be tricky, contact SMK, or read up on the django template system if you need any help.
"""

content = """{% load donation_tags %}Hello {{ donor.contact_name }},

Thank you for your donation of {{ donation.amount }} during {{ event.name }}. We appreciate your support.

{% if prizes %}
Here are the prizes that this donation puts you to towards:
  {% for prizeentry in prizes %}
{% if prizeentry.prize.ticketdraw %}(ticket){% else %}(time){% endif%} -- {{ prizeentry.amount | money }} towards {{ prizeentry.prize.name }}
  {% endfor %}
{% endif %}

Sincerely,
- The staff
"""

class Migration(DataMigration):

  def forwards(self, orm):
    "Write your forwards methods here."
    orm['post_office.EmailTemplate'].objects.create(name=defaultName, description=description, subject="Notification of Donation Receipt", content=content)

  def backwards(self, orm):
    "Write your backwards methods here."
    template = orm['post_office.EmailTemplate'].objects.filter(name=defaultName)
    if template.exists():
      template.delete()

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
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'post_office.emailtemplate': {
            'Meta': {'object_name': 'EmailTemplate'},
            'content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'html_content': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_updated': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'tracker.bid': {
            'Meta': {'ordering': "['event__date', 'speedrun__starttime', 'parent__name', 'name']", 'unique_together': "(('event', 'name', 'speedrun', 'parent'),)", 'object_name': 'Bid'},
            'biddependency': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'depedent_bids'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['tracker.Bid']"}),
            'count': ('django.db.models.fields.IntegerField', [], {}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'bids'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['tracker.Event']"}),
            'goal': ('django.db.models.fields.DecimalField', [], {'default': 'None', 'null': 'True', 'max_digits': '20', 'decimal_places': '2', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'istarget': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "'options'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['tracker.Bid']"}),
            'revealedtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'speedrun': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'bids'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['tracker.SpeedRun']"}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'OPENED'", 'max_length': '32'}),
            'total': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '20', 'decimal_places': '2'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'})
        },
        'tracker.bidsuggestion': {
            'Meta': {'ordering': "['name']", 'object_name': 'BidSuggestion'},
            'bid': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'suggestions'", 'on_delete': 'models.PROTECT', 'to': "orm['tracker.Bid']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'tracker.donation': {
            'Meta': {'ordering': "['-timereceived']", 'object_name': 'Donation'},
            'amount': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '20', 'decimal_places': '2'}),
            'bidstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '255'}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'commentlanguage': ('django.db.models.fields.CharField', [], {'default': "'un'", 'max_length': '32'}),
            'commentstate': ('django.db.models.fields.CharField', [], {'default': "'ABSENT'", 'max_length': '255'}),
            'currency': ('django.db.models.fields.CharField', [], {'max_length': '8'}),
            'domain': ('django.db.models.fields.CharField', [], {'default': "'LOCAL'", 'max_length': '255'}),
            'domainId': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '160', 'blank': 'True'}),
            'donor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Donor']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Event']", 'on_delete': 'models.PROTECT'}),
            'fee': ('django.db.models.fields.DecimalField', [], {'default': "'0.00'", 'max_digits': '20', 'decimal_places': '2'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modcomment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'readstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '255'}),
            'requestedalias': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'requestedemail': ('django.db.models.fields.EmailField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'requestedvisibility': ('django.db.models.fields.CharField', [], {'default': "'CURR'", 'max_length': '32'}),
            'testdonation': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'timereceived': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'transactionstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '64'})
        },
        'tracker.donationbid': {
            'Meta': {'ordering': "['-donation__timereceived']", 'object_name': 'DonationBid'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'bid': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bids'", 'on_delete': 'models.PROTECT', 'to': "orm['tracker.Bid']"}),
            'donation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bids'", 'on_delete': 'models.PROTECT', 'to': "orm['tracker.Donation']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'tracker.donor': {
            'Meta': {'ordering': "['lastname', 'firstname', 'email']", 'object_name': 'Donor'},
            'addresscity': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'addresscountry': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'addressstate': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'addressstreet': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'addresszip': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '128'}),
            'firstname': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastname': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'paypalemail': ('django.db.models.fields.EmailField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'runnertwitch': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'runnertwitter': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'runneryoutube': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'visibility': ('django.db.models.fields.CharField', [], {'default': "'FIRST'", 'max_length': '32'})
        },
        'tracker.donorcache': {
            'Meta': {'ordering': "('donor',)", 'unique_together': "(('event', 'donor'),)", 'object_name': 'DonorCache'},
            'donation_avg': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '2'}),
            'donation_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'donation_max': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '2'}),
            'donation_total': ('django.db.models.fields.DecimalField', [], {'default': '0', 'max_digits': '20', 'decimal_places': '2'}),
            'donor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Donor']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Event']", 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'tracker.event': {
            'Meta': {'ordering': "('date',)", 'object_name': 'Event'},
            'date': ('django.db.models.fields.DateField', [], {}),
            'donationemailsender': ('django.db.models.fields.EmailField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'donationemailtemplate': ('django.db.models.fields.related.ForeignKey', [], {'default': 'None', 'to': u"orm['post_office.EmailTemplate']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'locked': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
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
        'tracker.postbackurl': {
            'Meta': {'object_name': 'PostbackURL'},
            'event': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'postbacks'", 'to': "orm['tracker.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200'})
        },
        'tracker.prize': {
            'Meta': {'ordering': "['event__date', 'startrun__starttime', 'starttime', 'name']", 'unique_together': "(('name', 'event'),)", 'object_name': 'Prize'},
            'acceptemailsent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.PrizeCategory']", 'null': 'True', 'on_delete': 'models.PROTECT', 'blank': 'True'}),
            'creator': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'creatoremail': ('django.db.models.fields.EmailField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'creatorwebsite': ('django.db.models.fields.CharField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'endrun': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prize_end'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['tracker.SpeedRun']"}),
            'endtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'estimatedvalue': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '2', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Event']", 'on_delete': 'models.PROTECT'}),
            'extrainfo': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'imagefile': ('django.db.models.fields.files.FileField', [], {'max_length': '100', 'null': 'True', 'blank': 'True'}),
            'maximumbid': ('django.db.models.fields.DecimalField', [], {'default': "'5.0'", 'null': 'True', 'max_digits': '20', 'decimal_places': '2', 'blank': 'True'}),
            'maxwinners': ('django.db.models.fields.IntegerField', [], {'default': '1'}),
            'minimumbid': ('django.db.models.fields.DecimalField', [], {'default': "'5.0'", 'max_digits': '20', 'decimal_places': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'provided': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True', 'blank': 'True'}),
            'provideremail': ('django.db.models.fields.EmailField', [], {'max_length': '128', 'null': 'True', 'blank': 'True'}),
            'randomdraw': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'startrun': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prize_start'", 'null': 'True', 'on_delete': 'models.PROTECT', 'to': "orm['tracker.SpeedRun']"}),
            'starttime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'state': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '32'}),
            'sumdonations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'ticketdraw': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        'tracker.prizecategory': {
            'Meta': {'object_name': 'PrizeCategory'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'tracker.prizeticket': {
            'Meta': {'ordering': "['-donation__timereceived']", 'unique_together': "(('prize', 'donation'),)", 'object_name': 'PrizeTicket'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'donation': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tickets'", 'on_delete': 'models.PROTECT', 'to': "orm['tracker.Donation']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prize': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'tickets'", 'on_delete': 'models.PROTECT', 'to': "orm['tracker.Prize']"})
        },
        'tracker.prizewinner': {
            'Meta': {'unique_together': "(('prize', 'winner'),)", 'object_name': 'PrizeWinner'},
            'acceptstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '64'}),
            'emailsent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prize': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Prize']", 'on_delete': 'models.PROTECT'}),
            'shippingcost': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '20', 'decimal_places': '2', 'blank': 'True'}),
            'shippingemailsent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'shippingstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '64'}),
            'trackingnumber': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'winner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Donor']", 'on_delete': 'models.PROTECT'})
        },
        'tracker.speedrun': {
            'Meta': {'ordering': "['event__date', 'starttime']", 'unique_together': "(('name', 'event'),)", 'object_name': 'SpeedRun'},
            'deprecated_runners': ('django.db.models.fields.CharField', [], {'max_length': '1024', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'blank': 'True'}),
            'endtime': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Event']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'runners': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'to': "orm['tracker.Donor']", 'null': 'True', 'blank': 'True'}),
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
