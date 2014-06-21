from rest_framework import viewsets
from rest_framework import mixins
from rest_framework.settings import api_settings
from .serializers import MenuItemSerializer
from .models import MenuItem


class ReadOnlyMenuItemViewSet(mixins.RetrieveModelMixin,
                              mixins.ListModelMixin,
                              viewsets.GenericViewSet):
    queryset = MenuItem.objects.select_related('site')
    lookup_field = 'menu_slug'
    serializer_class = MenuItemSerializer
    paginate_by = api_settings.PAGINATE_BY or 10
    paginate_by_param = api_settings.PAGINATE_BY_PARAM or 'page'
