'''
Handle taxonomy container elements within forms
'''

from django.db import  router, transaction

from django import forms
from django.urls import reverse
from django.contrib import messages
from django.forms import TypedChoiceField, TypedMultipleChoiceField

from . import fields
from .views import GenericTitleSearchJSONView
from . import api
from .inlinetemplates import link, submit, tmpl_instance_message


class ElementForm(forms.Form):
    '''
    Associate elements with taxonomy terms
    '''
    term_pk = fields.IDTitleAutocompleteField(label='Term', min_value=0,
      #ajax_href='bluh',
      help_text="Id of a category for an element."
      )
      
    element_pk = fields.IDTitleAutocompleteField(label='Element', min_value=0,
      #ajax_href='grab',
      help_text="Id of an element to be categorised."
      )

    #def __init__(self, *args, **kwargs):
    #  super().__init__(*args, **kwargs)

from django.views.generic.edit import FormView
from django.views.generic.base import View
from django.http import  HttpResponseRedirect #Http404,



          
def ElementView(base_pk, element_title_url, ok_url, nav_links=[]):
    '''
    A view with two AJAX HTML inputs for adding Models as elements in a 
    taxonomy. In english, 'add the id of an item to a category in the trees'.
    
    On correct configuration, this view also deletes.
    
    @param element_title_url where the element input finds AJAX info. Sensitive... 
    @param nav_links links for the navigation bar. Can be anything. Must be full-rendered.
    '''
    class ElementView(FormView):
        template_name = 'taxonomy/generic_form.html'
        form_class = ElementForm
        success_url = ok_url
        
        def __init__(self, **kwargs):
            super().__init__(**kwargs)

        def get_form(self, form_class=None):
            f = super().get_form(form_class)
            f.fields['term_pk'].widget = fields.IDTitleAutocompleteInput('/taxonomy/base/'  + str(base_pk) + '/term_titles/json/search')
            f.fields['element_pk'].widget = fields.IDTitleAutocompleteInput(element_title_url)
            return f

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context['media'] = context['form'].media                
            context.update({
            'title': 'Add or reposition Elements',
            'navigators': nav_links,
            'submit': {'message':"Save", 'url': reverse('taxonomy-add-delete')},
            'actions': [submit('Delete', 'delete', attrs={'class':'"button alert"'})],
            })    
            return context
             
        def form_valid(self, form):
            # This method is called when valid form data has been POSTed.
            # It should return an HttpResponse.
            tpk = int(form.cleaned_data['term_pk'])
            epk = int(form.cleaned_data['element_pk'])
            # detect second submit          
            if (self.request.POST.get('delete')):
                with transaction.atomic(using=router.db_for_write(Element)):
                    #return _element_delete(request, base_pk, element_pk)
                    #api.element_delete(tpk, epk)
                    api.ElementAPI(epk).delete(tpk)
                msg = "Deleted Link"
                messages.add_message(self.request, messages.SUCCESS, msg)
                return HttpResponseRedirect(reverse('taxonomy-add-delete'))
            else:
                #api.element_add(tpk, epk)
                api.ElementAPI(epk).add(tpk)
                msg = tmpl_instance_message("Associated Element Id {0} to Term".format(epk), tpk)
                messages.add_message(self.request, messages.SUCCESS, msg)
                return super().form_valid(form)
    return ElementView

from django.conf.urls import url

def get_urls(model, base_pk, navigation_links=[]):
    element_name = model._meta.model_name
    title_url = '/' + element_name + '/titles/json/search'
    v = ElementView(
      base_pk=base_pk,
      element_title_url=title_url,
      ok_url='/' + element_name +'/taxonomy/add-delete',
      nav_links = navigation_links
      )
    urls = [
        url(r'^taxonomy/add-delete$', v.as_view(), name='taxonomy-add-delete'),
        #url(r'^taxonomy/term/(?P<term_pk>\d+)/element/(?P<element_pk>\d+)/delete$', dv.as_view(), name='taxonomy-element-delete'),
        url(r'^titles/json/search$', GenericTitleSearchJSONView(model, 'title').as_view(), name='paper-titles-json'),
    ]
    return urls
      
#-
#def merge(request, base_pk):
    #'''
    #Associate a pk for a foreign element with a term.
    #In english, 'add the id of an item to a category in the trees'.
    #Since the id only is used, there is no data to 'update', so this 
    #method is called 'merge'. If the id is already attached to the term
    #it will not be duplicated.
    #'''
    #try:
        #bm = api.base(base_pk)
    #except Base.DoesNotExist:
        #msg = "Base with ID '{0}' doesn't exist?".format(
            #base_pk
        #)
        #messages.add_message(request, messages.WARNING, msg) 
        ##! sort something here
        ##return HttpResponseRedirect(reverse('base-list'))
        #return 404
        
    #if request.method == 'POST':
        ## submitted data, populate
        #f = ElementForm(request.POST)

        ### check whether it's valid:
        #if f.is_valid():
            #api.element_merge(
                #term_pks=[f.cleaned_data['term_pk']], 
                #element_pk=f.cleaned_data['element_pk']
                #) 
            #t = api.term(f.cleaned_data['pk'])
            #msg = tmpl_instance_message("Associated Element Id {0} to Term".format(f.cleaned_data['element']), t.title)
            #messages.add_message(request, messages.SUCCESS, msg)
            ##return HttpResponseRedirect(reverse('term-list', args=[t.tree]))
            #return 404
        #else:
            #msg = "Please correct the errors below."
            #messages.add_message(request, messages.ERROR, msg)
            ## falls through to another render
            
    #else:
        ## empty form for add
        #f = ElementForm(initial=dict(
          #pk = tm.pk,
          #title = tm.title,
          ## set parents to the root (always exists, as an option) 
          #element = 0,
          #))
        
    #context={
    #'form': f,
    #'title': 'Add or reposition Elements',
    #'navigators': [
      #link('Main List', reverse('term-list', args=[tm.tree])),
      #],
    #'submit': {'message':"Save", 'url': reverse('element-merge', args=[tm.pk])},
    #'actions': [],
    #}

    #return render(request, 'taxonomy/generic_form.html', context)

#-
#def _element_delete(request, base_pk, element_pk):
      #try:
        #tm = Base.objects.get(pk__exact=base_pk)
      #except Base.DoesNotExist:
        #msg = "Base with ID '{0}' doesn't exist. Perhaps it was deleted?".format(
            #base_pk
        #)
        #messages.add_message(request, messages.WARNING, msg) 
        #return HttpResponseRedirect(reverse('tree-list'))
        
      #xterms = Element.system.tree_element_terms(tm.pk, element_pk)
      #if (not xterms):
        #msg = "Element with ID '{0}' not attached to any term in Base '{1}'. Perhaps it was deleted?".format(
            #element_pk,
            #html.escape(tm.title)
        #)
        #messages.add_message(request, messages.WARNING, msg) 
        #return HttpResponseRedirect(reverse('tree-list'))
        
      #if (request.method == 'POST'):
          ##Term.system.delete(tm.pk)
          #api.element_delete(base_pk=tm.pk, element_pks=element_pk)
          ##cache_clear_flat_tree(tm.tree)
          #msg = tmpl_instance_message("Deleted element link", element_pk)
          #messages.add_message(request, messages.SUCCESS, msg)
          #return HttpResponseRedirect(reverse('term-list', args=[tm.pk]))
      #else:
          #message = '<p>Are you sure you want to delete the element link "{0}" from the tree "{1}"?</p><p>The element is attached to terms named {2}</p>'.format(
            #html.escape(element_pk),
            #html.escape(tm.title),
            #html.escape('"' + '", "'.join([t[1] for t in xterms]) + '"')
            #)
          #context={
            #'title': tmpl_instance_message("Delete element link '{0}' from Base".format(element_pk), tm.title),
            #'message': mark_safe(message),
            #'submit': {'message':"Yes, I'm sure", 'url': reverse('element-delete', args=[tm.pk, element_pk])},
            #'actions': [link('No, take me back', reverse("element-merge", args=[tm.pk]), attrs={'class':'"button"'})],
          #} 
          #return render(request, 'taxonomy/delete_confirm_form.html', context)

#-
#@csrf_protect_m        
#def delete(request, base_pk, element_pk):
  ## Lock the DB. Found this in admin.
    #with transaction.atomic(using=router.db_for_write(Element)):
      #return _element_delete(request, base_pk, element_pk)
  

# from taxonomy import element
# from django.contrib.site import admin_wrap
#url(r'^admin/elements/merge$', ElementView.as_view(), {base_pk=26}, name='taxonomy-link-merge'),
#url(r'^admin/elements/(?P<element_pk>\d+)/delete$', admin_wrap(element.delete), {base_pk=26}, name='taxonomy-link-delete'),




def term_choices(base_api):
    '''
    Term data formatted for HTML selectors.
    Term pks from the tree. For general term parenting.
    
    @return list of (pk, title) from a tree.
    '''
    ftree = base_api.flat_tree()
    b = [(api.UNPARENT, '<not attached>')]
    [b.append((t.pk, ('-' * t.depth) + t.title)) for t in ftree]
    return b


def term_choice_value(base_api, model_instance):
    '''
    Value to be used in a multiple select button.
    For parenting elements.
    
    @return if instance is none, or a search for existing attached terms
    returns empty, then [api.UNPARENT], else [instance_parent_pk, ...]
    '''
    if (model_instance is None):
        return [api.UNPARENT]
    else:
        xt = base_api.element_terms(model_instance.pk)
        if (not xt):
            return [api.UNPARENT]
        return [t[0] for t in xt]

#! do we need this for element fields?
def form_set_select(form, taxonomy_field_name, base_pk, instance=None):
    '''
    @return a single or multi-selector field with choices. Widget is
    a default HTML 'select'.
    '''
    #assert base(base_pk) is not None, "base_pk can not be found: base_pk:{0}".format(base_pk)
    bapi = api.BaseAPI(base_pk)
    if (bapi.is_single):
      field = TypedChoiceField(
      coerce=lambda val: int(val), 
      empty_value=-2,
      label='Taxonomy',
      help_text="Choose a term to parent this item"
      )
    else:
      field = TypedMultipleChoiceField(
      coerce=lambda val: int(val), 
      empty_value=-2,
      label='Taxonomy',
      help_text="Choose a term to parent this item"
      )
    form.fields[taxonomy_field_name] = field
    form.fields[taxonomy_field_name].choices = term_choices(bapi)
    form.initial[taxonomy_field_name] = term_choice_value(bapi, instance)
        
def save(form, taxonomy_field_name, base_pk, obj):
    #assert base(base_pk) is not None, "base_pk can not be found: base_pk:{0}".format(base_pk)
    eapi = api.ElementAPI(obj.pk)
    eapi.base_delete(base_pk)
    taxonomy_terms = form.cleaned_data.get(taxonomy_field_name)
    if(taxonomy_terms is None):
        raise KeyError('Unable to find clean data for taxonomy parenting: field_name : {0}'.format(base_pk))
    if (not isinstance(taxonomy_terms, list)):
        taxonomy_terms = [taxonomy_terms]
    if (-2 not in taxonomy_terms):
        eapi.merge(taxonomy_terms)

def remove(base_pk, obj):
    #assert base(base_pk) is not None, "base_pk can not be found: tree_pk:{0}".format(base_pk)
    eapi = api.ElementAPI(obj.pk)
    eapi.base_delete(base_pk)
