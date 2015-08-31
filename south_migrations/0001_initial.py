# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Event'
        db.create_table('tracker_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('short', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('chipinid', self.gf('django.db.models.fields.CharField')(max_length=128, unique=True, null=True, blank=True)),
            ('scheduleid', self.gf('django.db.models.fields.CharField')(max_length=128, unique=True, null=True, blank=True)),
            ('scheduledatetimefield', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('schedulegamefield', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('schedulerunnersfield', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('scheduleestimatefield', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('schedulesetupfield', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('schedulecommentatorsfield', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('schedulecommentsfield', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('date', self.gf('django.db.models.fields.DateField')()),
        ))
        db.send_create_signal('tracker', ['Event'])

        # Adding model 'Challenge'
        db.create_table('tracker_challenge', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('speedrun', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.SpeedRun'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('goal', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=2)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=1024, null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('pin', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('tracker', ['Challenge'])

        # Adding unique constraint on 'Challenge', fields ['speedrun', 'name']
        db.create_unique('tracker_challenge', ['speedrun_id', 'name'])

        # Adding model 'ChallengeBid'
        db.create_table('tracker_challengebid', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('challenge', self.gf('django.db.models.fields.related.ForeignKey')(related_name='bids', to=orm['tracker.Challenge'])),
            ('donation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Donation'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=2)),
        ))
        db.send_create_signal('tracker', ['ChallengeBid'])

        # Adding model 'Choice'
        db.create_table('tracker_choice', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('speedrun', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.SpeedRun'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=1024, null=True, blank=True)),
            ('state', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('pin', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('tracker', ['Choice'])

        # Adding unique constraint on 'Choice', fields ['speedrun', 'name']
        db.create_unique('tracker_choice', ['speedrun_id', 'name'])

        # Adding model 'ChoiceBid'
        db.create_table('tracker_choicebid', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('option', self.gf('django.db.models.fields.related.ForeignKey')(related_name='bids', to=orm['tracker.ChoiceOption'])),
            ('donation', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Donation'])),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=2)),
        ))
        db.send_create_signal('tracker', ['ChoiceBid'])

        # Adding model 'ChoiceOption'
        db.create_table('tracker_choiceoption', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('choice', self.gf('django.db.models.fields.related.ForeignKey')(related_name='option', to=orm['tracker.Choice'])),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('tracker', ['ChoiceOption'])

        # Adding unique constraint on 'ChoiceOption', fields ['choice', 'name']
        db.create_unique('tracker_choiceoption', ['choice_id', 'name'])

        # Adding model 'Donation'
        db.create_table('tracker_donation', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('donor', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Donor'])),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Event'])),
            ('domain', self.gf('django.db.models.fields.CharField')(default='LOCAL', max_length=255)),
            ('domainId', self.gf('django.db.models.fields.CharField')(unique=True, max_length=160, blank=True)),
            ('bidstate', self.gf('django.db.models.fields.CharField')(default='PENDING', max_length=255)),
            ('readstate', self.gf('django.db.models.fields.CharField')(default='PENDING', max_length=255)),
            ('commentstate', self.gf('django.db.models.fields.CharField')(default='PENDING', max_length=255)),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=20, decimal_places=2)),
            ('timereceived', self.gf('django.db.models.fields.DateTimeField')()),
            ('comment', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('modcomment', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('tracker', ['Donation'])

        # Adding model 'Donor'
        db.create_table('tracker_donor', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(unique=True, max_length=128)),
            ('alias', self.gf('django.db.models.fields.CharField')(max_length=32, unique=True, null=True, blank=True)),
            ('firstname', self.gf('django.db.models.fields.CharField')(max_length=32, null=True, blank=True)),
            ('lastname', self.gf('django.db.models.fields.CharField')(max_length=32)),
            ('anonymous', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('tracker', ['Donor'])

        # Adding model 'Prize'
        db.create_table('tracker_prize', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
            ('category', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.PrizeCategory'], null=True, blank=True)),
            ('sortkey', self.gf('django.db.models.fields.IntegerField')(default=0, db_index=True)),
            ('image', self.gf('django.db.models.fields.URLField')(max_length=1024, null=True, blank=True)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=1024, null=True, blank=True)),
            ('minimumbid', self.gf('django.db.models.fields.DecimalField')(default='5.0', max_digits=20, decimal_places=2)),
            ('maximumbid', self.gf('django.db.models.fields.DecimalField')(default='5.0', max_digits=20, decimal_places=2)),
            ('sumdonations', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('randomdraw', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Event'])),
            ('startrun', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='prize_start', null=True, to=orm['tracker.SpeedRun'])),
            ('endrun', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='prize_end', null=True, to=orm['tracker.SpeedRun'])),
            ('starttime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('endtime', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('winner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Donor'], null=True, blank=True)),
            ('pin', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('provided', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('emailsent', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('tracker', ['Prize'])

        # Adding unique constraint on 'Prize', fields ['category', 'winner', 'event']
        db.create_unique('tracker_prize', ['category_id', 'winner_id', 'event_id'])

        # Adding model 'PrizeCategory'
        db.create_table('tracker_prizecategory', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
        ))
        db.send_create_signal('tracker', ['PrizeCategory'])

        # Adding model 'SpeedRun'
        db.create_table('tracker_speedrun', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('runners', self.gf('django.db.models.fields.CharField')(max_length=1024)),
            ('sortkey', self.gf('django.db.models.fields.IntegerField')(db_index=True)),
            ('description', self.gf('django.db.models.fields.TextField')(max_length=1024, blank=True)),
            ('event', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['tracker.Event'])),
            ('starttime', self.gf('django.db.models.fields.DateTimeField')()),
            ('endtime', self.gf('django.db.models.fields.DateTimeField')()),
        ))
        db.send_create_signal('tracker', ['SpeedRun'])

        # Adding unique constraint on 'SpeedRun', fields ['name', 'event']
        db.create_unique('tracker_speedrun', ['name', 'event_id'])

        # Adding model 'UserProfile'
        db.create_table('tracker_userprofile', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('user', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.User'], unique=True)),
            ('prepend', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
        ))
        db.send_create_signal('tracker', ['UserProfile'])


    def backwards(self, orm):
        # Removing unique constraint on 'SpeedRun', fields ['name', 'event']
        db.delete_unique('tracker_speedrun', ['name', 'event_id'])

        # Removing unique constraint on 'Prize', fields ['category', 'winner', 'event']
        db.delete_unique('tracker_prize', ['category_id', 'winner_id', 'event_id'])

        # Removing unique constraint on 'ChoiceOption', fields ['choice', 'name']
        db.delete_unique('tracker_choiceoption', ['choice_id', 'name'])

        # Removing unique constraint on 'Choice', fields ['speedrun', 'name']
        db.delete_unique('tracker_choice', ['speedrun_id', 'name'])

        # Removing unique constraint on 'Challenge', fields ['speedrun', 'name']
        db.delete_unique('tracker_challenge', ['speedrun_id', 'name'])

        # Deleting model 'Event'
        db.delete_table('tracker_event')

        # Deleting model 'Challenge'
        db.delete_table('tracker_challenge')

        # Deleting model 'ChallengeBid'
        db.delete_table('tracker_challengebid')

        # Deleting model 'Choice'
        db.delete_table('tracker_choice')

        # Deleting model 'ChoiceBid'
        db.delete_table('tracker_choicebid')

        # Deleting model 'ChoiceOption'
        db.delete_table('tracker_choiceoption')

        # Deleting model 'Donation'
        db.delete_table('tracker_donation')

        # Deleting model 'Donor'
        db.delete_table('tracker_donor')

        # Deleting model 'Prize'
        db.delete_table('tracker_prize')

        # Deleting model 'PrizeCategory'
        db.delete_table('tracker_prizecategory')

        # Deleting model 'SpeedRun'
        db.delete_table('tracker_speedrun')

        # Deleting model 'UserProfile'
        db.delete_table('tracker_userprofile')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'tracker.challenge': {
            'Meta': {'ordering': "['speedrun__sortkey', 'name']", 'unique_together': "(('speedrun', 'name'),)", 'object_name': 'Challenge'},
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'goal': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'pin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'speedrun': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.SpeedRun']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'tracker.challengebid': {
            'Meta': {'ordering': "['-donation__timereceived']", 'object_name': 'ChallengeBid'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'challenge': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bids'", 'to': "orm['tracker.Challenge']"}),
            'donation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Donation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'tracker.choice': {
            'Meta': {'unique_together': "(('speedrun', 'name'),)", 'object_name': 'Choice'},
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'pin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'speedrun': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.SpeedRun']"}),
            'state': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'tracker.choicebid': {
            'Meta': {'ordering': "['option__choice__speedrun__sortkey', 'option__choice__name']", 'object_name': 'ChoiceBid'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'donation': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Donation']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'option': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'bids'", 'to': "orm['tracker.ChoiceOption']"})
        },
        'tracker.choiceoption': {
            'Meta': {'unique_together': "(('choice', 'name'),)", 'object_name': 'ChoiceOption'},
            'choice': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'option'", 'to': "orm['tracker.Choice']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        },
        'tracker.donation': {
            'Meta': {'ordering': "['-timereceived']", 'object_name': 'Donation'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '20', 'decimal_places': '2'}),
            'bidstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '255'}),
            'comment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'commentstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '255'}),
            'domain': ('django.db.models.fields.CharField', [], {'default': "'LOCAL'", 'max_length': '255'}),
            'domainId': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '160', 'blank': 'True'}),
            'donor': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Donor']"}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modcomment': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'readstate': ('django.db.models.fields.CharField', [], {'default': "'PENDING'", 'max_length': '255'}),
            'timereceived': ('django.db.models.fields.DateTimeField', [], {})
        },
        'tracker.donor': {
            'Meta': {'ordering': "['lastname', 'firstname', 'email']", 'object_name': 'Donor'},
            'alias': ('django.db.models.fields.CharField', [], {'max_length': '32', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'anonymous': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'email': ('django.db.models.fields.EmailField', [], {'unique': 'True', 'max_length': '128'}),
            'firstname': ('django.db.models.fields.CharField', [], {'max_length': '32', 'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lastname': ('django.db.models.fields.CharField', [], {'max_length': '32'})
        },
        'tracker.event': {
            'Meta': {'object_name': 'Event'},
            'chipinid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'date': ('django.db.models.fields.DateField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'schedulecommentatorsfield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'schedulecommentsfield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'scheduledatetimefield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'scheduleestimatefield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'schedulegamefield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'scheduleid': ('django.db.models.fields.CharField', [], {'max_length': '128', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'schedulerunnersfield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'schedulesetupfield': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'short': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'tracker.prize': {
            'Meta': {'ordering': "['event__date', 'sortkey', 'name']", 'unique_together': "(('category', 'winner', 'event'),)", 'object_name': 'Prize'},
            'category': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.PrizeCategory']", 'null': 'True', 'blank': 'True'}),
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'emailsent': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'endrun': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prize_end'", 'null': 'True', 'to': "orm['tracker.SpeedRun']"}),
            'endtime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.URLField', [], {'max_length': '1024', 'null': 'True', 'blank': 'True'}),
            'maximumbid': ('django.db.models.fields.DecimalField', [], {'default': "'5.0'", 'max_digits': '20', 'decimal_places': '2'}),
            'minimumbid': ('django.db.models.fields.DecimalField', [], {'default': "'5.0'", 'max_digits': '20', 'decimal_places': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'}),
            'pin': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'provided': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'randomdraw': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'sortkey': ('django.db.models.fields.IntegerField', [], {'default': '0', 'db_index': 'True'}),
            'startrun': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'prize_start'", 'null': 'True', 'to': "orm['tracker.SpeedRun']"}),
            'starttime': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'sumdonations': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'winner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Donor']", 'null': 'True', 'blank': 'True'})
        },
        'tracker.prizecategory': {
            'Meta': {'object_name': 'PrizeCategory'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        },
        'tracker.speedrun': {
            'Meta': {'ordering': "['event__date', 'sortkey', 'starttime']", 'unique_together': "(('name', 'event'),)", 'object_name': 'SpeedRun'},
            'description': ('django.db.models.fields.TextField', [], {'max_length': '1024', 'blank': 'True'}),
            'endtime': ('django.db.models.fields.DateTimeField', [], {}),
            'event': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['tracker.Event']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'runners': ('django.db.models.fields.CharField', [], {'max_length': '1024'}),
            'sortkey': ('django.db.models.fields.IntegerField', [], {'db_index': 'True'}),
            'starttime': ('django.db.models.fields.DateTimeField', [], {})
        },
        'tracker.userprofile': {
            'Meta': {'object_name': 'UserProfile'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'prepend': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['tracker']