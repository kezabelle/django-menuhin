from rest_framework import serializers
from django.contrib.sites.models import Site
from .models import MenuItem


class MenuItemSerializer(serializers.HyperlinkedModelSerializer):
    object_url = serializers.SerializerMethodField('get_object_url')
    path = serializers.CharField(source='uri')
    depth = serializers.Field(source='depth')
    root = serializers.Field(source='is_root')
    child = serializers.SerializerMethodField('is_child_node')
    descendants = serializers.SerializerMethodField('get_descendant_count')
    ancestors = serializers.SerializerMethodField('get_ancestor_count')

    def is_child_node(self, obj):
        return obj.depth > 1

    def get_descendant_count(self, obj):
        return obj.get_descendants().count()

    def get_ancestor_count(self, obj):
        return obj.get_ancestors().count()

    def get_object_url(self, obj):
        request = self.context.get('request', None)
        url = obj.get_canonical_url()
        if request is None:
            return url
        return '{scheme}:{path}'.format(scheme=request.scheme, path=url)

    class Meta:
        model = MenuItem
        lookup_field = 'menu_slug'
        fields = ['created', 'modified', 'url', 'object_url', 'title',
                  'menu_slug', 'path', 'depth', 'root', 'child', 'descendants', 'ancestors']
