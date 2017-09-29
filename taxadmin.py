from django.db import  router, transaction #models,
from django.views.generic import TemplateView

from .models import Term, Base, TermParent, BaseTerm#, Element
from django import forms
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils import html
from django.urls import reverse
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import render
from . import api
#? only for select choices?
#from. import views
from django.forms import TypedChoiceField, TypedMultipleChoiceField
from .inlinetemplates import link, submit, tmpl_instance_message

#! work to do deleteView etc?
#! not in admin permissions

class TermListView(TemplateView):
  template_name = "taxonomy/term_list.html"
  
  def get_context_data(self, **kwargs):
      tree1 = api.base(int(kwargs['base_pk']))
      if (tree1 == None):
        #? cannt redirect in this view?
        raise Http404(tmpl_404_redirect_message(Base))   
        
      context = super(TermListView, self).get_context_data(**kwargs)
      context['title'] = tmpl_instance_message("Terms in", tree1.title)
      context['tools'] = [link('Add', reverse('term-add', args=[tree1.pk]))]
      context['headers'] = [mark_safe('TITLE'), mark_safe('ACTION')]
      context['messages'] = messages.get_messages(self.request)
      context['navigators'] = [link('Base List', reverse('base-list'))]

      ## form of rows
      # - name with view link
      # - tid parent depth (all hidden)
      # - 'edit' link
      rows = []
      
      # Term row displays come in two forms...
      if (not tree1.is_single):
        # multiple can not show the structure of the tree
        # (...could if the tree is small, but let's be consistent)
        #term_data_queryset = Term.objects.order_by('weight', 'title').filter(base__exact=tree1.pk).values_list('pk', 'title')
        term_data_queryset = api.base_terms_ordered(tree1.pk)
        for o in term_data_queryset:
          pk = o[0]
          rows.append({
            'view': link(o[1], reverse('term-preview', args=[pk])),
            'edit': link('edit', reverse('term-edit', args=[pk]))
          })    
      else:
        # single parentage can show the structure of the tree
            #! can be none

        ftree = api.terms_flat_tree(tree1.pk)
        
        for td in ftree: 
          #? Unicode nbsp is probably not long-term viable
          # but will do for now
          title = '\u00A0' * (td.depth*2)  + td.title          
          pk = td.pk
          # (extra context data here in case we enable templates/JS etc.)
          rows.append({
            'view': link(title, reverse('term-preview', args=[pk])),
            'termpk': pk,
            'depth': td.depth,
            'edit': link('edit', reverse('term-edit', args=[pk]))
          })
      context['rows'] = rows
      
      return context

def term_all_select(base_pk):
    '''
    All titles from a tree.
    The titles have a representation of structure by indenting with '-'.    
    Intended for single parent select boxes.

    @param base_pk int or coercable string
    @return [(pk, marked title)...]
    '''
    tree = api.terms_flat_tree(base_pk)
    b = [(TermParent.NO_PARENT, '<root>')]    
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
    tpk = int(term_pk)
    bpk = int(base_pk)
    desc_pks = api.term_descendant_pks(bpk, tpk)
    desc_pks.add(tpk)
    ftree = api.terms_flat_tree(bpk)
    b = [(TermParent.NO_PARENT, '<root>')]    
    for t in ftree:
        if (t.pk not in desc_pks):
            b.append((t.pk, ('-'*t.depth) + t.title)) 
    return b
    
    
def form_field_parent_select(base, term_pk=None):
    '''
    @return a single or multi-selector field with term widget
    '''
    if (term_pk is None):
        choices = term_all_select(base.pk)
    else:
        choices = term_exclusive_select(base.pk, term_pk)
    if (base.is_single):
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
      
    #! how big is the field?
    #base = forms.IntegerField(min_value=0, widget=forms.HiddenInput())
    
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
    
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
      
      #base = kwargs['initial']['base']
      #term_pk = kwargs['initial'].get('pk')
      # set form field type
      # default is single parent. If multiple parent, override with
      # multiple-select.
      
      # set choices
      #pk = kwargs['initial'].get('pk')
      #if(pk is not None):
          # update form. root and targeted choices
      #    self.fields['parents'].choices = views.term_exclusive_select(term(pk))
      #else:
          # create form. root and all term choices.
      #    self.fields['parents'].choices = views.term_all_select(base_pk) 

 
def term_add(request, base_pk):
    b = api.base(base_pk)
    if (b == None):
        msg = "Base with ID '{0}' doesn't exist.".format(b.pk)
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('term-list', args=[b.pk]))

    if request.method == 'POST':
        # submitted data, populate
        f = TermForm(request.POST,
            initial=dict(
                      #base = b.pk,
                      )
            )
        f.fields['parents'] = form_field_parent_select(b)

        ## check whether it's valid:
        if f.is_valid():
            #t = Term.system.create(
            t = api.term_create(
                base_pk=b.pk, 
                parent_pks=f.cleaned_data['parents'],
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
            
            #cache_clear_flat_tree(b.pk)
          
            msg = tmpl_instance_message("Created new Term", t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[b.pk]))
            
        else:
            msg = "Please correct the errors below."
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
            
    else:
        # empty form for add
        f = TermForm(initial=dict(
          weight = 0,
          # set parents to the root (always exists, as an option) 
          parents = [TermParent.NO_PARENT],
          ))
        f.fields['parents'] = form_field_parent_select(b)

    context={
    'form': f,
    'title': 'Add Term',
    'navigators': [
      link('Term List', reverse('term-list', args=[b.pk])),
      ],
    'submit': {'message':"Save", 'url': reverse('term-add', args=[b.pk])},
    'actions': [],
    }    

    return render(request, 'taxonomy/generic_form.html', context)



def term_edit(request, term_pk):
    try:
      tm = Term.objects.get(pk__exact=term_pk)
    except Term.DoesNotExist:
        msg = "Term with ID '{0}' doesn't exist.".format(term_pk)
        messages.add_message(request, messages.WARNING, msg)        
        # must be base-list, no tree id to work with 
        return HttpResponseRedirect(reverse('base-list'))
            
    b = api.base(api.term_base_pk(term_pk))
            
    if request.method == 'POST':
        f = TermForm(request.POST,
            initial=dict(
              #base = b
              )
        )
        f.fields['parents'] = form_field_parent_select(b, term_pk)
        if (not f.is_valid()):
            #print('cleaned data:')
            #print(str(f.cleaned_data))
            msg = "Term failed to validate?"
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
            
        else:
            #! validate
            # - parent not between trees
            # - parent not child of itself
            #if (f.fields['treepk'].has_changed()):
            #! handle mutiple            
            #t = Term.system.update(
            t = api.term_update(
                #treepk=f.cleaned_data['base'], 
                parent_pks=f.cleaned_data['parents'], 
                term_pk=tm.pk, 
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
            
            #cache_clear_flat_tree(b)

            msg = tmpl_instance_message("Updated Term", t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[b.pk]))
            
    else:
        # requested update form
        initial = dict(
            # this field triggers modified parent widgets
            pk=tm.pk,
            title=tm.title,
            slug=tm.slug,
            description=tm.description,
            weight=tm.weight,
            parents=api.term_parent_pks(b.pk, tm.pk)
          )
        # add in the non-model treepk field inits
        #initial['parents'] = term_parent_data(b, tm.pk)
        #set field type
        #initial['parents'] = term_exclusive_select(tm)

        #set initial data
        f = TermForm(initial=initial)
        f.fields['parents'] = form_field_parent_select(b, term_pk)
        
    context={
    'form': f,
    'title': tmpl_instance_message('Edit term', tm.title),
    'navigators': [
      link('Base List', reverse('base-list')),
      link('Term List', reverse('term-list', args=[b.pk]))
      ],
    'submit': {'message':"Save", 'url': reverse('term-edit', args=[tm.pk])},
    'actions': [link('Delete', reverse("term-delete", args=[tm.pk]), attrs={'class':'"button alert"'})],
    }
    
    return render(request, 'taxonomy/generic_form.html', context)


def _term_delete(request, term_pk):
      try:
        tm = Term.objects.get(pk__exact=term_pk)
      except Term.DoesNotExist:
        msg = "Term with ID '{0}' doesn't exist. Perhaps it was deleted?".format(
            term_pk
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('base-list'))
      b = BaseTerm.system.base(tm.pk)
      
      if (request.method == 'POST'):
          #Term.system.delete(tm.pk)
          api.term_delete(tm.pk)
          #cache_clear_flat_tree(b)
          msg = tmpl_instance_message("Deleted Term", tm.title)
          messages.add_message(request, messages.SUCCESS, msg)
          return HttpResponseRedirect(reverse('term-list', args=[b]))
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


#@csrf_protect_m        
def term_delete(request, pk):
    with transaction.atomic(using=router.db_for_write(Term)):
      return _term_delete(request, pk)
  


      
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
      #tree_queryset = Base.objects.order_by('weight', 'title').values_list('pk', 'title')
      base_queryset = api.base_ordered()
      for o in base_queryset:
          pk = o.pk
          rows.append({
            'pk': pk,
            'title': o.title,
            #'weight': e.weight,
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
            #t = Base.system.create(
            t = api.base_create(
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                is_single=f.cleaned_data['is_single'],
                weight=f.cleaned_data['weight']
                ) 
            #cache_clear_tree_cache()
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
    try:
      tm = Base.objects.get(pk__exact=base_pk)
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
                #! need warning...
                return HttpResponseRedirect(reverse('base-tosingleparent', args=[tm.pk]))
                
            #t = Base.system.update(
            t = api.base_update(
                base_pk=tm.pk, 
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                is_single=f.cleaned_data['is_single'],
                weight=f.cleaned_data['weight']
                ) 
            #cache_clear_tree_cache()
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
      try:
        tm = Base.objects.get(pk__exact=base_pk)
      except Exception as e:
        msg = "{0} with ID '{1}' doesn't exist. Perhaps it was deleted?".format('Base', tm.pk)
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('base-list'))
             
      if (request.method == 'POST'):
          #Base.system.delete(tm.pk)
          api.base_delete(tm.pk)
          #cache_clear_flat_tree(tm.pk)
          #cache_clear_tree_cache()
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
def base_delete(request,base_pk):
    #? lock what? How?
    with transaction.atomic(using=router.db_for_write(Base)):
      return _base_delete(request, base_pk)
      


def _base_to_single_parent(request, base_pk):
      try:
        tm = Base.objects.get(pk__exact=base_pk)
      except Base.DoesNotExist:
        msg = "Base with ID '{0}' doesn't exist. Perhaps it was deleted?".format(
            base_pk
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('base-list'))
        
      if (request.method == 'POST'):
          count = TermParent.system.multiple_to_single(tm.pk)
          api.base_set_is_single(tm.pk, True)
          msg = tmpl_instance_message("Base is now single parent. Deleted {0} parent(s) in".format(count), tm.title)
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
    with transaction.atomic(using=router.db_for_write(TermParent)):
      return _base_to_single_parent(request, base_pk)
  
