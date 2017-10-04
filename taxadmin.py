from django.db import  router, transaction #models,
from django.views.generic import TemplateView

from .models import Term, Base #, TermParent, BaseTerm, Element
from django import forms
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils import html
from django.urls import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from . import api
from django.forms import TypedChoiceField, TypedMultipleChoiceField
from .inlinetemplates import link, submit, tmpl_instance_message


#! build rows in code. These templates are pointless.
class TermListView(TemplateView):
    template_name = "taxonomy/term_list.html"
  
    def get_context_data(self, **kwargs):
        bapi = api.BaseAPI(kwargs['base_pk'])
        try:
            bm = bapi.base()
        except Exception as e:
            #? cannt redirect in this view?
            raise Http404(tmpl_404_redirect_message(Base))   
          
        context = super(TermListView, self).get_context_data(**kwargs)
        context['title'] = tmpl_instance_message("Terms in", bm.title)
        context['tools'] = [link('Add', reverse('term-add', args=[bm.pk]))]
        context['headers'] = [mark_safe('TITLE'), mark_safe('ACTION')]
        context['messages'] = messages.get_messages(self.request)
        context['navigators'] = [link('Base List', reverse('base-list'))]
  
        ## form of rows
        # - name with view link
        # - tid parent depth (all hidden)
        # - 'edit' link
        rows = []
        
        # Term row displays come in two forms...
        if (not bapi.is_single):
          # multiple can not show the structure of the tree
          # (...could if the tree is small, but let's be consistent)
          term_data_queryset = bapi.terms_ordered()
          for o in term_data_queryset:
            pk = o[0]
            rows.append({
              'view': o[1],
              'edit': link('edit', reverse('term-edit', args=[pk]))
            })    
        else:
          # single parentage can show the structure of the tree
              #! can be none
  
          ftree = bapi.flat_tree()
          
          for td in ftree: 
            #? Unicode nbsp is probably not long-term viable
            # but will do for now
            title = '\u00A0' * (td.depth*2)  + html.escape(td.title)          
            pk = td.pk
            # (extra context data here in case we enable templates/JS etc.)
            rows.append({
              'view': title,
              'termpk': pk,
              'depth': td.depth,
              'edit': link('edit', reverse('term-edit', args=[pk]))
            })
        context['rows'] = rows
        return context

def term_all_select(base_api):
    '''
    All titles from a tree.
    The titles have a representation of structure by indenting with '-'.    
    Intended for single parent select boxes.

    @param base_pk int or coercable string
    @return [(pk, marked title)...]
    '''
    tree = base_api.flat_tree()
    b = [(api.ROOT, '<root>')]    
    for e in tree:
        b.append((e.pk, '-'*e.depth + html.escape(e.title)))  
    return b

def term_exclusive_select(base_pk, term_pk):
    '''
    Term data formatted for HTML selectors.
    Term pks from the tree but not a descendent of the given term_pk.
    For parenting terms, to avoid child clashes.
    
    @return list of (pk, title) from a tree which do not descend from, 
    or include, the given term_pk.
    '''
    # This value is mainly for the elimination of child selections when
    # choosing terms (to avoid circular dependencies)
    tapi = api.TermAPI(term_pk, base_pk)
    bapi = api.BaseAPI(base_pk)
    desc_pks = tapi.descendant_pks()
    desc_pks.add(tapi.pk)
    ftree = bapi.flat_tree()
    b = [(api.ROOT, '<root>')]    
    for t in ftree:
        if (t.pk not in desc_pks):
            b.append((t.pk, ('-'*t.depth) + t.title)) 
    return b
    
    
def form_field_parent_select(base_api, term_pk=None):
    '''
    @return a single or multi-selector field with term widget
    '''
    if (term_pk is None):
        choices = term_all_select(base_api)
    else:
        choices = term_exclusive_select(base_api.pk, term_pk)
    if (base_api.is_single):
      return TypedChoiceField(
      choices = choices,
      coerce=lambda val: int(val), 
      empty_value=-1,
      label='Parent',
      help_text="Category above ('root' is top-level)."
      )
    else:
      return TypedMultipleChoiceField(
      choices = choices,
      coerce=lambda val: int(val), 
      empty_value=-1,
      label='Parents',
      help_text="Category above ('root' is top-level)."
      )

class TermForm(forms.Form):
    '''
    Required in initial is a 'tree' attribute.
    
    Optional is a 'pk' attribute. With the 'pk' attribute, an 'update' 
    form is built. Without the 'pk' attribute, a 'create' form is built. 
    
    Also optional: the populating values for the fields from the model 
    Term (title, slug, description).
    '''
    parents = forms.TypedChoiceField(
      help_text="Category above ('root' is top-level)."
      )
      
    title = forms.CharField(label='Title', max_length=64,
      help_text="Name for the category. Limited to 255 characters."
      )
    
    slug = forms.SlugField(label='Slug', max_length=64,
      help_text="Short name for use in urls."
      )
      
    description = forms.CharField(required= False, label='Description', max_length=255,
      help_text="Description of the category. Limited to 255 characters."
      )
    
    weight = forms.IntegerField(label='Weight', min_value=0, max_value=32767,
      help_text="Priority for display in some templates. Lower value orders first. 0 to 32767."
      )
    
    


 
def term_add(request, base_pk):
    bapi = api.BaseAPI(base_pk)
    try:
        bm = bapi.base()
    except Exception:
        msg = "Base with ID '{0}' doesn't exist.".format(base_pk)
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('term-list', args=[base_pk]))

    if request.method == 'POST':
        f = TermForm(request.POST,
            initial=dict(
                      #base = b.pk,
                      )
            )
        f.fields['parents'] = form_field_parent_select(bapi)

        if f.is_valid():
            t = bapi.term_create(
                #base_pk=bm.pk, 
                parent_pks=f.cleaned_data['parents'],
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                )
            msg = tmpl_instance_message("Created new Term", t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[bm.pk]))
            
        else:
            msg = "Please correct the errors below."
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
            
    else:
        # empty form for add
        f = TermForm(initial=dict(
          weight = 0,
          # set parents to the root (always exists, as an option) 
          parents = [api.ROOT],
          ))
        f.fields['parents'] = form_field_parent_select(bapi)

    context={
    'form': f,
    'title': 'Add Term',
    'navigators': [
      link('Term List', reverse('term-list', args=[bm.pk])),
      ],
    'submit': {'message':"Save", 'url': reverse('term-add', args=[bm.pk])},
    'actions': [],
    }    

    return render(request, 'taxonomy/generic_form.html', context)





def term_edit(request, term_pk):
    tapi = api.TermAPI(term_pk)
    try:
        tm = tapi.term()
    except Term.DoesNotExist:
        msg = "Term with ID '{0}' doesn't exist.".format(term_pk)
        messages.add_message(request, messages.WARNING, msg)        
        # must be base-list, no tree id to work with 
        return HttpResponseRedirect(reverse('base-list'))
            
    bpk = tapi.base_pk()
    bapi = api.BaseAPI(bpk)
            
    if request.method == 'POST':
        f = TermForm(request.POST,
            initial=dict(
              #base = b
              )
        )
        f.fields['parents'] = form_field_parent_select(bapi, tm.pk)
        if (not f.is_valid()):
            msg = "Term failed to validate?"
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
            
        else:
            #! validate
            # - parent not between trees
            # - parent not child of itself
            t = tapi.update(
                parent_pks=f.cleaned_data['parents'], 
                #term_pk=tm.pk, 
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
            msg = tmpl_instance_message("Updated Term", t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[bpk]))
            
    else:
        # requested update form
        initial = dict(
            title=tm.title,
            slug=tm.slug,
            description=tm.description,
            weight=tm.weight,
            parents=tapi.parent_pks()
          )

        #set initial data
        f = TermForm(initial=initial)
        f.fields['parents'] = form_field_parent_select(bapi, tm.pk)
        
    context={
    'form': f,
    'title': tmpl_instance_message('Edit term', tm.title),
    'navigators': [
      link('Base List', reverse('base-list')),
      link('Term List', reverse('term-list', args=[bpk]))
      ],
    'submit': {'message':"Save", 'url': reverse('term-edit', args=[tm.pk])},
    'actions': [link('Delete', reverse("term-delete", args=[tm.pk]), attrs={'class':'"button alert"'})],
    }
    
    return render(request, 'taxonomy/generic_form.html', context)


def _term_delete(request, term_pk):
    tapi = api.TermAPI(term_pk)
    try:
        tm = tapi.term()
    except Term.DoesNotExist:
        msg = "Term with ID '{0}' doesn't exist. Perhaps it was deleted?".format(
            term_pk
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('base-list'))
    bpk = tapi.base_pk()
      
    if (request.method == 'POST'):
        api.term_delete(tm.pk)
        msg = tmpl_instance_message("Deleted Term", tm.title)
        messages.add_message(request, messages.SUCCESS, msg)
        return HttpResponseRedirect(reverse('term-list', args=[bpk]))
    else:
        message = '<p>Are you sure you want to delete the Term "{0}"?</p><p>Deleting a term will delete all its term children if there are any. This action cannot be undone.</p><p>(deleting a term will not delete elements attached to the term. However, attached elements will be removed from the taxonomies)</p>'.format(
          html.escape(tm.title)
          )
        context={
          'title': tmpl_instance_message("Delete term", tm.title),
          'message': mark_safe(message),
          'submit': {'message':"Yes, I'm sure", 'url': reverse('term-delete', args=[tm.pk])},
          'actions': [link('No, take me back', reverse("term-edit", args=[tm.pk]), attrs={'class':'"button"'})],
        } 
        return render(request, 'taxonomy/delete_confirm_form.html', context)


        
def term_delete(request, term_pk):
    with transaction.atomic(using=router.db_for_write(Term)):
      return _term_delete(request, term_pk)
  


#! build rows in code. This template is pointless.
class BaseListView(TemplateView):
  template_name = "taxonomy/tree_list.html"

  def get_context_data(self, **kwargs):
      context = super(BaseListView, self).get_context_data(**kwargs)

      context['title'] = 'Base List'
      context['tools'] = [link('Add', reverse('base-add'))]
      context['headers'] = [mark_safe('TITLE'), mark_safe('ACTION'), mark_safe(''), mark_safe('')]
      #context['navigators'] = [mark_safe('<a href="/taxonomy/tree/list"/>tree list</a>')]
      context['messages'] = messages.get_messages(self.request)
      rows = []
      base_queryset = api.Taxonomy.ordered()
      for o in base_queryset:
          pk = o.pk
          rows.append({
            'pk': pk,
            'title': o.title,
            'edit': link('edit', reverse('base-edit', args=[pk])),
            'list': link('list terms', reverse('term-list', args=[pk])),
            'add': link('add terms', reverse('term-add', args=[pk]))
          })       
      context['rows'] = rows
      return context



class BaseForm(forms.Form):
    '''
    Required in initial is a 'tree' attribute.
    
    Optional is a 'pk' attribute. With the 'pk' attribute, an 'update' 
    form is built. Without the 'pk' attribute, a 'create' form is built. 
    
    Also optional: the populating values for the fields from the model 
    Term (title, slug, description).
    '''
    # help data from model?    
    title = forms.CharField(label='Title', max_length=64,
      help_text="Name for the category. Limited to 255 characters."
      )
    
    slug = forms.SlugField(label='Slug', max_length=64,
      help_text="Short name for use in urls."
      )
      
    description = forms.CharField(required= False, label='Description', max_length=255,
      help_text="Description of the category. Limited to 255 characters."
      )
      
    is_single = forms.BooleanField(label='Single Parent',
      required=False,
      help_text="Nunber of parents allowed for a term in the taxonomy (True = one only, False = many).",
      )
          
    weight = forms.IntegerField(label='Weight', min_value=0, max_value=32767,
      help_text="Priority for display in some templates. Lower value orders first. 0 to 32767."
      )

    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      
      if (kwargs.get('initial') and 'pk' in kwargs['initial']):
        self.fields['pk'] = forms.IntegerField(min_value=0, widget=forms.HiddenInput())



def base_add(request):
    if request.method == 'POST':
        f = BaseForm(request.POST)
        if f.is_valid():
            t = api.Taxonomy.base_create(
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                is_single=f.cleaned_data['is_single'],
                weight=f.cleaned_data['weight']
                ) 
            msg = tmpl_instance_message("Created new Base", t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('base-list'))
        else:
            msg = "Please correct the errors below."
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
    else:
        # empty form for add
        f = BaseForm(initial=dict(is_single=True,weight=0))
        
    context={
    'form': f,
    'title': 'Add Base',
    'navigators': [
      link('Base List', reverse('base-list')),
      ],
    'submit': {'message':"Save", 'url': reverse('base-add')},
    'actions': [],
    }    

    return render(request, 'taxonomy/generic_form.html', context)
    


def base_edit(request, base_pk):
    bapi = api.BaseAPI(base_pk)
    try:
        tm = bapi.base()
    except Base.DoesNotExist:
        msg = "Base with ID '{0}' doesn't exist.".format(base_pk)
        messages.add_message(request, messages.WARNING, msg)        
        return HttpResponseRedirect(reverse('base-list'))
            
    if request.method == 'POST':
        # create a form instance and validate
        f = BaseForm(request.POST,
            initial=dict(
              pk = tm.pk
              )
        )
        if (not f.is_valid()):
            msg = "Base failed to validate?"
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
        else:
            #print('haschanged:')
            sgl = f.cleaned_data['is_single']
            if (
                f.fields['is_single'].has_changed(tm.is_single, sgl)
                and sgl == True
                ):
                return HttpResponseRedirect(reverse('base-tosingleparent', args=[tm.pk]))
                
            t = bapi.update(
                #base_pk=tm.pk, 
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                is_single=f.cleaned_data['is_single'],
                weight=f.cleaned_data['weight']
                ) 
            msg = tmpl_instance_message("Update tree", f.cleaned_data['title'])
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('base-list'))
    else:
        # requested update form
        initial = dict(
            pk=tm.pk,
            title=tm.title,
            slug=tm.slug,
            description=tm.description,
            is_single=tm.is_single,
            weight=tm.weight
          )
        # add in the non-model treepk field inits
        f = BaseForm(initial=initial)

    context={
    'form': f,
    'title': tmpl_instance_message('Edit tree', tm.title),
    'navigators': [
      link('Base List', reverse('base-list')),
      link('Term List', reverse('term-list', args=[tm.pk]))
      ],
    'submit': {'message':"Save", 'url': reverse('base-edit', args=[tm.pk])},
    'actions': [link('Delete', reverse("base-delete", args=[tm.pk]), attrs={'class':'"button alert"'})],
    }
    
    return render(request, 'taxonomy/generic_form.html', context)



def _base_delete(request, base_pk):
    bapi = api.BaseAPI(base_pk)
    try:
      tm = bapi.base()
    except Exception as e:
      msg = "{0} with ID '{1}' doesn't exist. Perhaps it was deleted?".format('Base', tm.pk)
      messages.add_message(request, messages.WARNING, msg) 
      return HttpResponseRedirect(reverse('base-list'))
           
    if (request.method == 'POST'):
        bapi.delete()
        msg = tmpl_instance_message("Deleted tree", tm.title)
        messages.add_message(request, messages.SUCCESS, msg)
        return HttpResponseRedirect(reverse('base-list'))
    else:
        message = '<p>Are you sure you want to delete the Base "{0}"?</p><p>Deleting a tree will delete all its term children if there are any. This action cannot be undone.</p><p>(deleting a tree will not delete elements attached to the terms)</p>'.format(
            html.escape(tm.title)
            )    
        context={
          'title': tmpl_instance_message("Delete tree", tm.title),
          'message': mark_safe(message),
          'submit': {'message':"Yes, I'm sure", 'url': reverse('base-delete', args=[tm.pk])},
          'actions': [link('No, take me back', reverse("base-edit", args=[tm.pk]), attrs={'class':'"button"'})],
        } 
        return render(request, 'taxonomy/delete_confirm_form.html', context)


#@csrf_protect_m  
def base_delete(request, base_pk):
    #? lock what? How?
    with transaction.atomic(using=router.db_for_write(Base)):
      return _base_delete(request, base_pk)
      


def _base_to_single_parent(request, base_pk):
    bapi = api.BaseAPI(base_pk)
    try:
      tm = bapi.base()
    except Base.DoesNotExist:
      msg = "Base with ID '{0}' doesn't exist. Perhaps it was deleted?".format(
          base_pk
      )
      messages.add_message(request, messages.WARNING, msg) 
      return HttpResponseRedirect(reverse('base-list'))
      
    if (request.method == 'POST'):
        #count = TermParent.system.multiple_to_single(tm.pk)
        #count = TermParent.system.multiple_to_single(tm.pk)
        #api.base_set_is_single(tm.pk, True)
        bapi.is_single = True 
        #msg = tmpl_instance_message("Base is now single parent. Deleted {0} parent(s) in".format(count), tm.title)
        msg = tmpl_instance_message("Base is now single parent ", tm.title)
        messages.add_message(request, messages.SUCCESS, msg)
        return HttpResponseRedirect(reverse('term-list', args=[tm.pk]))
    else:
        message = '<p>Are you sure you want to convert the Base "{0}"?</p><p>Converting to single parent will remove duplicate parents.</p><p>The parents to remove can not be selected. If you wish to affect parentage, then edit term parents (delete to one parant) before converting the tree.</p><p>(this action will not affect elements attached to the terms)</p>'.format(
          html.escape(tm.title)
          )
        context={
          'title': tmpl_instance_message("Convert to single parent tree", tm.title),
          'message': mark_safe(message),
          'submit': {'message':"Yes, I'm sure", 'url': reverse('base-tosingleparent', args=[tm.pk])},
          'actions': [link('No, take me back', reverse("base-edit", args=[tm.pk]), attrs={'class':'"button"'})],
        } 
        return render(request, 'taxonomy/delete_confirm_form.html', context)


#@csrf_protect_m        
def base_to_singleparent(request, base_pk):
    with transaction.atomic(using=router.db_for_write(Base)):
      return _base_to_single_parent(request, base_pk)
  
