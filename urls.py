from django.conf.urls import url
from generic_view_template.views import GenericObjectView, GenericQuerySetAnchorView
from generic_view_template import rend

from . import views

urlpatterns = [
    url(r'^base/(?P<base_pk>\d+)/term_titles/json/search$', views.term_title_search_view, name='term-titles-startswith-json'),
]
