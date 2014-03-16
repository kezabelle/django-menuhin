# from .admin import *
from .context_processors import *
from .middleware import *
from .utils import *
from .models import *
from .forms import *
# from .signals import *
from .sitemaps import *
from .templatetags import *
# from .views import *

try:
    from unittest import TestCase
except ImportError:
    from django.utils.unittest import TestCase
import menuhin


class VersionTestCase(TestCase):
    def test_usage(self):
        self.assertEqual(menuhin.get_version(), menuhin.version)
        self.assertEqual(menuhin.__version_info__, menuhin.__version__)

