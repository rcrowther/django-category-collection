from django.conf.urls import url
from django.views.decorators.cache import never_cache

#treelist_view, treeadd_view # tree_view #, TermDetailView
from generic_view_template.views import GenericObjectView, GenericQuerySetAnchorView
#from taxonomy.views import TermListView #, ElementSearchView

from taxonomy.taxadmin import BaseListView, TermListView #, ElementSearchView

from taxonomy.models import Term, Base
from generic_view_template import rend

from . import views
from . import taxadmin
from . import site

urlpatterns = site.get_urls()
