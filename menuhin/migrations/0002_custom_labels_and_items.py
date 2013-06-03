# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'CustomMenuItem'
        db.create_table('menuhin_custommenuitem', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('menu', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['menuhin.Menu'])),
            ('position', self.gf('django.db.models.fields.CharField')(default='above', max_length=5)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=2048)),
            ('parent_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('menuhin', ['CustomMenuItem'])

        # Adding model 'CustomMenuLabel'
        db.create_table('menuhin_custommenulabel', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('menu', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['menuhin.Menu'])),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('target_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('menuhin', ['CustomMenuLabel'])


    def backwards(self, orm):
        # Deleting model 'CustomMenuItem'
        db.delete_table('menuhin_custommenuitem')

        # Deleting model 'CustomMenuLabel'
        db.delete_table('menuhin_custommenulabel')


    models = {
        'menuhin.custommenuitem': {
            'Meta': {'object_name': 'CustomMenuItem'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'menu': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['menuhin.Menu']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'parent_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'position': ('django.db.models.fields.CharField', [], {'default': "'above'", 'max_length': '5'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '2048'})
        },
        'menuhin.custommenulabel': {
            'Meta': {'object_name': 'CustomMenuLabel'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'menu': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['menuhin.Menu']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'target_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'menuhin.menu': {
            'Meta': {'object_name': 'Menu'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'display_title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sites.Site']"}),
            'title': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'})
        },
        'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['menuhin']