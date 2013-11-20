# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Menu'
        db.create_table(u'menuhin_menu', (
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('site', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sites.Site'])),
            ('title', self.gf('django.db.models.fields.SlugField')(max_length=50, primary_key=True)),
            ('display_title', self.gf('django.db.models.fields.CharField')(max_length=50)),
        ))
        db.send_create_signal(u'menuhin', ['Menu'])

        # Adding unique constraint on 'Menu', fields ['site', 'title']
        db.create_unique(u'menuhin_menu', ['site_id', 'title'])

        # Adding model 'CustomMenuItem'
        db.create_table(u'menuhin_custommenuitem', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('modified', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('is_published', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('menu', self.gf('django.db.models.fields.related.ForeignKey')(related_name='menu_items', to=orm['menuhin.Menu'])),
            ('position', self.gf('django.db.models.fields.CharField')(default='above', max_length=5)),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('url', self.gf('django.db.models.fields.CharField')(max_length=2048)),
            ('target_id', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('attach_menu', self.gf('django.db.models.fields.related.ForeignKey')(related_name='attached_to', null=True, to=orm['menuhin.Menu'])),
        ))
        db.send_create_signal(u'menuhin', ['CustomMenuItem'])


    def backwards(self, orm):
        # Removing unique constraint on 'Menu', fields ['site', 'title']
        db.delete_unique(u'menuhin_menu', ['site_id', 'title'])

        # Deleting model 'Menu'
        db.delete_table(u'menuhin_menu')

        # Deleting model 'CustomMenuItem'
        db.delete_table(u'menuhin_custommenuitem')


    models = {
        u'menuhin.custommenuitem': {
            'Meta': {'object_name': 'CustomMenuItem'},
            'attach_menu': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'attached_to'", 'null': 'True', 'to': u"orm['menuhin.Menu']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'menu': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'menu_items'", 'to': u"orm['menuhin.Menu']"}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'position': ('django.db.models.fields.CharField', [], {'default': "'above'", 'max_length': '5'}),
            'target_id': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'url': ('django.db.models.fields.CharField', [], {'max_length': '2048'})
        },
        u'menuhin.menu': {
            'Meta': {'unique_together': "(('site', 'title'),)", 'object_name': 'Menu'},
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'display_title': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'is_published': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'modified': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'site': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['sites.Site']"}),
            'title': ('django.db.models.fields.SlugField', [], {'max_length': '50', 'primary_key': 'True'})
        },
        u'sites.site': {
            'Meta': {'ordering': "('domain',)", 'object_name': 'Site', 'db_table': "'django_site'"},
            'domain': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        }
    }

    complete_apps = ['menuhin']