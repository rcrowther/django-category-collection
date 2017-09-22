from django.conf.urls import url
from django.views.decorators.cache import never_cache

#treelist_view, treeadd_view # tree_view #, TermDetailView
from generic_view_template.views import GenericObjectView, GenericQuerySetAnchorView
from taxonomy.views import TreeListView, TermListView #, ElementSearchView
from taxonomy.models import Term, Tree
from generic_view_template import rend

from . import views

urlpatterns = [
  #? Not working as generic view?
  #url(r'^taxonomies/$', TaxonomyList.as_view(), name='taxonomy-list'),
  
  #url(r'^$', treelist_view),
  #url(r'^add/$', treeadd_view),
  #url(r'^(?P<slug>[-\w]+)/change/$', treechange_view),
  #url(r'^$', taxonomy_list, name='taxonomy-list'),
  #url(r'^tree/$', taxonomy_list, name='taxonomy-list'),
  #url(r'^tree/(?P<slug>[-\w]+)/$', tree_view, name='term-detail'),
  #url(r'^term/$', term_list, name='term-detail'),
  #url(r'^term/(?P<slug>[-\w]+)/$', TermDetailView.as_view(), name='term-detail'),
  #url(r'^term/(?P<slug>[-\w]+)/$', GenericObjectView.as_view(model=Term), name='term-detail'),

  #'admin/content/taxonomy' 
  # taxonomies list with CUD buttons
  # /admin/taxonomy/ -> an *all models* choose list
  # actually at /admin/taxonomy/tree/
  
  #'admin/content/taxonomy/add/vocabulary'
  # C taxonomy
  # /admin/taxonomy/tree/add/
  
  #'admin/content/taxonomy/edit/vocabulary/%taxonomy_vocabulary'
  # U taxonomy
  # /admin/taxonomy/tree/%tree/change/

  #admin/content/taxonomy/%taxonomy_vocabulary
  # U term hierarchy
  # /admin/taxonomy/tree/%tree/ -> Needs heavy adaption so list can be adapted 
    
  #'admin/content/taxonomy/%taxonomy_vocabulary/add/term'
  # C term
  # /admin/taxonomy/%tree/term/add/
  
  # 'taxonomy/term/%'
  # R Term
  
  #'admin/content/taxonomy/edit/term'
  # U term
  # /admin/taxonomy/term/%term/change/

  # Can be provided by:
  # Taxonomy
  # /admin/taxonomy/   - list
  # /admin/taxonomy/add/  - add
  # /admin/taxonomy/%taxonomy/change/  - change
  # Term
  # /admin/taxonomy/%taxonomy/term/   - list
  # /admin/taxonomy/%taxonomy/term/add/  - add
  # /admin/taxonomy/%taxonomy/term/%term/change/  - change  
  # So can autogenerate URLS
  # Would be nice if base URL coud be modified for ordering?
  # or extra URL?
  # /admin/taxonomy/%taxonomy/term/order   - list ordering
  #?
  # We need customisable URLs
  # Direct access to modelAdmin, not overall model lists
  # Then the potential to override each URL for model lists
  # and the addList itself
  
  # BluntAdmin(model)
  #url(r'^admin/$', views.model_admin2.changelist_view),

  #url(r'^term/$', GenericQuerySetAnchorView.as_view(model=Term, field="title")),
  #url(r'^term/(?P<pk>[-\w]+)/$', GenericObjectView.as_view(model=Term,)),
  
  # Order is important, actions before slugs
  url(r'^element/(?P<element_pk>\d+)$', never_cache(views.element_link), name='element-link'),
  #url(r'^element/(?P<element_pk>\d+)$', never_cache(ElementSearchView.as_view()), name='element-link'),
  url(r'^term_titles/(?P<tree_pk>\d+)$', never_cache(views.tree_term_titles_view), name='term-titles'),
  #url(r'^term_titles_ajax/(?P<tree_pk>\d+)$', never_cache(views.tree_term_titles_istartswith_view), name='term-titles-startswith'),

  url(r'^term/(?P<term_pk>\d+)/element/merge/$', never_cache(views.element_merge), name='element-merge'),
  url(r'^tree/(?P<tree_pk>\d+)/element/(?P<element_pk>\d+)/delete/$', views.element_delete, name='element-delete'),

  url(r'^tree/(?P<tree_pk>\d+)/term/list/$', never_cache(TermListView.as_view()), name='term-list'),
  url(r'^term/(?P<term_pk>\d+)/edit/$', never_cache(views.term_edit), name='term-edit'),
  url(r'^term/(?P<pk>\d+)/delete/$', views.term_delete, name='term-delete'),
  url(r'^tree/(?P<tree_pk>\d+)/term/add/$', never_cache(views.term_add), name='term-add'),
  url(r'^term/(?P<pk>\d+)/$', GenericObjectView.as_view(model=Term,), name='term-preview'),
  url(r'^term/(?P<slug>[-\w]+)/$', GenericObjectView.as_view(model=Term,), name='term-detail'),

  url(r'^tree/list/$',  never_cache(TreeListView.as_view()), name='tree-list'),
  url(r'^tree/(?P<tree_pk>\d+)/edit/$', never_cache(views.tree_edit), name='tree-edit'),
  url(r'^tree/(?P<tree_pk>\d+)/delete/$', views.tree_delete, name='tree-delete'),
  url(r'^tree/(?P<tree_pk>\d+)/tosingleparent/$', views.tree_tosingleparent, name='tree-tosingleparent'),
  url(r'^tree/add/$', never_cache(views.tree_add), name='tree-add'),
  url(r'^tree/(?P<slug>[-\w]+)/$', GenericObjectView.as_view(model=Tree,), name='tree-detail'),

  url(r'^$', never_cache(TreeListView.as_view()), name='tree-list'),


  #url(r'^article/(?P<pk>[-\w]+)/$', GenericObjectView.as_view(model=Paper, renderers={'image': rend.empty, 'mini_image_url': rend.as_image })),
  # admin/taxonomy/id list of terms
  # edit/term/id
]
