from functools import update_wrapper

from django.conf.urls import url, include
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.http import Http404, HttpResponseRedirect
from django.urls import NoReverseMatch, reverse

try:
    from django.contrib.admin import site
except ImportError:
    site = None

from generic_view_template.views import GenericObjectView
from taxonomy.models import Term, Base
from . import views
from taxonomy.taxadmin import BaseListView, TermListView
from . import taxadmin
    
def _admin_view(view, cacheable=False, admin_site=site):
    """
    Decorator to create an admin view attached to an ``AdminSite``. 
    This wraps the view and provides optional caching and permission
    checking by calling ``site.has_permission``.

    You'll want to use this from within ``AdminSite.get_urls()``:

        class MyAdminSite(AdminSite):

            def get_urls(self):
                from django.conf.urls import url

                urls = super().get_urls()
                urls += [
                    url(r'^my_view/$', self.admin_view(some_view))
                ]
                return urls

    By default, admin_views are marked non-cacheable using the
    ``never_cache`` decorator. If the view can be safely cached, set
    cacheable=True.
    """
    def inner(request, *args, **kwargs):
        if ((site is not None) and (not site.has_permission(request))):
            if request.path == reverse('admin:logout', current_app=site.name):
                index_path = reverse('admin:index', current_app=site.name)
                return HttpResponseRedirect(index_path)
            # Inner import to prevent django.contrib.admin (app) from
            # importing django.contrib.auth.models.User (unrelated model).
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(
                request.get_full_path(),
                reverse('admin:login', current_app=site.name)
            )
        return view(request, *args, **kwargs)
    if not cacheable:
        inner = never_cache(inner)
    # We add csrf_protect here so this function can be used as a utility
    # function for any view, without having to repeat 'csrf_protect'.
    if not getattr(view, 'csrf_exempt', False):
        inner = csrf_protect(inner)
    return update_wrapper(inner, view)
    
def get_urls(admin_site=site):
  
    def wrap(view, cacheable=False, admin_site=site):
        def wrapper(*args, **kwargs):
            return _admin_view(view, cacheable, admin_site)(*args, **kwargs)
        wrapper.admin_site = admin_site
        return update_wrapper(wrapper, view)
  
    urls = [
        # Order is important, actions before slugs
        #? Nothing is cacheable
        #url(r'^element/(?P<element_pk>\d+)$', wrap(views.element_link), name='element-link'),
        #url(r'^element/(?P<element_pk>\d+)$', wrap(ElementSearchView.as_view()), name='element-link'),
        #url(r'^term_titles/(?P<base_pk>\d+)$', wrap(views.term_title_search_view), name='term-titles'),
        url(r'^base/(?P<base_pk>\d+)/term_titles/json/search$', wrap(views.term_title_search_view), name='term-titles-startswith-json'),
        
        #url(r'^term/(?P<term_pk>\d+)/element/merge/$', wrap(views.element_merge), name='element-merge'),
        #url(r'^base/(?P<base_pk>\d+)/element/(?P<element_pk>\d+)/delete/$', wrap(views.element_delete), name='element-delete'),
        
        url(r'^base/(?P<base_pk>\d+)/term/list/$', wrap(TermListView.as_view()), name='term-list'),
        url(r'^base/(?P<base_pk>\d+)/term/add/$', wrap(taxadmin.term_add), name='term-add'),
        url(r'^term/(?P<term_pk>\d+)/edit/$', wrap(taxadmin.term_edit), name='term-edit'),
        url(r'^term/(?P<pk>\d+)/delete/$', wrap(taxadmin.term_delete), name='term-delete'),
        url(r'^term/(?P<pk>\d+)/$', wrap(GenericObjectView.as_view(model=Term,)), name='term-preview'),
        url(r'^term/(?P<slug>[-\w]+)/$', wrap(GenericObjectView.as_view(model=Term,)), name='term-detail'),
        
        url(r'^base/list/$',  wrap(BaseListView.as_view()), name='base-list'),
        url(r'^base/add/$', wrap(taxadmin.base_add), name='base-add'),
        url(r'^base/(?P<base_pk>\d+)/edit/$', wrap(taxadmin.base_edit), name='base-edit'),
        url(r'^base/(?P<base_pk>\d+)/delete/$', wrap(taxadmin.base_delete), name='base-delete'),
        url(r'^base/(?P<base_pk>\d+)/tosingleparent/$', wrap(taxadmin.base_to_singleparent), name='base-tosingleparent'),
        url(r'^base/(?P<slug>[-\w]+)/$', wrap(GenericObjectView.as_view(model=Base,)), name='base-detail'),
        
        url(r'^$', wrap(BaseListView.as_view()), name='base-list'),
    ]
    return urls

