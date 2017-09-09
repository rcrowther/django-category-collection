from django.shortcuts import render

# Create your views here.

from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.urls import reverse
from django.http import Http404
from django.utils import html
from django.utils.safestring import mark_safe
from itertools import chain

from .models import Term, Tree, TermParent

from django.http import HttpResponseRedirect



#from generictemplates import object_fields

#TODO:
# autoslug
# add delete action?
# check against options
# multi-step deletion?
# overview
# adjust Term to reflect tree source
# paginate
# reverse all redirects?
#? term list display indents
# consider redirects, and messages on term pages?

    
########################################
## helpers

  
def tree_terms_for_element(tree_pk, epk):
  '''
  Get terms associated with an element, within a tree.
  Ordered by weight.
  
  @return queryset of terms
  '''
  term_ids = TermNode.objects.filter(node__exact=epk).values_list('term', flat=True)
  return Term.objects.order_by('weight').filter(tree__exact=tree_pk, pk__exact=term_ids)


def tree_term_titles(tree_pk):
  '''
  Get terms in a tree
  @return list of term data tuples (pk, title)
  '''
  return Term.objects.filter(tree__exact=tree_pk).values_list('pk', 'title', 'description')


# Cache of hierarchial associations
# cache{tree_id: {term_id: [associated_term_ids]}}
_children = {}
_parents = {}

# defo cache tree objects
# maybe cashe terms
from collections import namedtuple

_tree = {}
TreeData = namedtuple('TreeData', ['title', 'description', 'is_single', 'is_unique'])

def tree_data(treepk):
  d = _tree.get(treepk)
  if (not d):
    try:
      t = Tree.objects.get(pk__exact=treepk)
    except Tree.DoesNotExist:
      raise Http404('The requested admin page does not exist.')

    d = TreeData(t.title, t.description, t.is_single, t.is_unique)
    _tree[treepk] = d
  return d


_term = {}
TermData = namedtuple('TermData', ['title', 'description'])

def term_data(termpk):
  d = _term.get(termpk)
  if (not d):
    term = Term.objects.get(pk__exact=termpk)
    d = TermData(term.title, term.description)
    _term[termpk] = d
  return d
  

  
def cache_clear_on_update():
  '''
  No need to empty term cache.
  '''
  _children = {}
  _parents = {}
  _tree = {}
  
  
def cache_clear_tree():
  '''
  If trees are updated or created, no effect on term cache. 
  '''
  _tree = {}

def cache_clear():
  cache_clear_on_update()
  _term = {}

# probably want term_children? all_term_children?
def children(treepk):
  return _children[treepk]

  
def parents(treepk):
  return _parents[treepk]

TermFTData = namedtuple('TermFTData', ['pk', 'depth', 'parents'])
    
#? rename terms_flat_tree?
def tree_terms_ordered(tree_pk, parent_pk=TermParent.NO_PARENT, max_depth=-1):
  '''
  Return data from Terms as a flat tree.
  Each item is an TermFTData (Term 'pk' extended with 'depth' and
  'parents' attributes).
  Note that depth starts at 0.
  
  @param parent_pk start from the children of this term.
  @param max_depth prune the tree beyond this value. Corresponds with
   depth (value 0 will print one row, if data is available, at depth 0) 
  @return list of TermFTData(termpk, depth. [parent_ids]). Root ids will
   be parented by [-1].
  '''
  cached = _children.get(tree_pk)
  if (not cached):
    #treeterm_pks = TermTree.objects.filter(tree__exact=tree_pk)
    term_pks = Term.objects.order_by('weight', 'title').filter(tree__exact=tree_pk).values_list('pk', flat=True)
    term_parents = TermParent.objects.filter(term__in=term_pks)
    #print(str(TermParent.objects.filter(term__in=term_pks).query))
    # ensure we start with -1 kv present, we may look for that
    # as default
    _children[tree_pk] = {-1:[]}
    _parents[tree_pk] = {}
    for e in term_parents:
      if (e.parent in _children[tree_pk]):
        _children[tree_pk][e.parent].append(e.term)
      else:
        _children[tree_pk][e.parent] = [e.term]
      if (e.term in _parents[tree_pk]):
        _parents[tree_pk][e.term].append(e.parent)
      else:
        _parents[tree_pk][e.term] = [e.parent]

  children = _children[tree_pk]
  parents = _parents[tree_pk]
  _max_depth =  len(children) if max_depth < 0 else max_depth
  tree = []

  if (not parent_pk in children):
    # parent_pk was probably a leaf, return empty
    return tree
    
  # Stack of levels to process. Each level is an iter.
  # preload with the first set of children
  child_pks = children[parent_pk]
  stack = [iter(child_pks)]

  while stack:
    it = stack.pop()
    depth = len(stack)

    while(True):
      try:
          pk = it.__next__()
      except StopIteration:
        break
      tree.append(TermFTData(pk, depth, parents[pk]))
      child_pks = children.get(pk)
      #print('max:')
      #print(str(_max_depth))
      #print(str(depth))
      if (depth < _max_depth and child_pks):
          # append current iter, to go back to
          stack.append(it)
          # append new depth of iter
          stack.append(iter(child_pks))
          break
        
  return tree
  

#def term_children_pk(termpk):

def term_parent_pks(tree_pk, pk):
  if (not tree_pk in _parents):
    tree_terms_ordered(tree_pk)
  #print('tree:')
  #print(str(_parents))
  return _parents[tree_pk][pk]
  
def term_node_count(termpk):
  return TermNode.objects.filter(term__exact=termpk).count()

#! filter for illegal where?  
def tree_term_select_titles(tree_pk, exclude=[]):
  '''
  List of titles in a tree.
  The titles have a representation of structure by indenting with '-'.
   
  @param exclude list of pks to remove from the list. Numeric type (not string)
  @return list [(pk, title)...]
  '''
  tree = tree_terms_ordered(tree_pk)
  #print('exclude:')
  #print(str(exclude))
  #? assert a root item? Can always be added here?
  b = [(-1, '<root>')]
  for e in tree:
    if (not e.pk in exclude):
      #print('pk:')
      #print(str(e.pk))
      name = html.escape(term_data(e.pk).title)
      b.append((e.pk, '-'*e.depth + name))
    
  return b
  #list(chain([(TermParent.NO_PARENT, 'root')], tree_term_titles(tree_pk)))

def term_descendant_pks(treepk, pk=TermParent.NO_PARENT):
    '''
    Find all descendants of a term
    @return list of child ids
    '''
    t = tree_terms_ordered(treepk, pk)
    return [e.pk for e in t]
    
def ancestor_pks(treepk, pk=TermParent.NO_PARENT):
    '''
    Find all parent anscestors
    @return list of child ids
    '''
    #t = tree_terms_ordered(treepk)
    #return [e.pk for e in t]
  
#-
def _term_delete(pk):
  stash=[pk]
  while stash:
    tpk = stash.pop()
    children = TermParent.objects.filter(parent__exact=tpk).values_list('term', flat=True)
    for c in children:
      parents_c = TermParent.objects.filter(term__exact=c).count()
      if ( parents_c < 2 ):
        stash.append(c)
    t = Term.objects.get(pk__exact=tpk)
    t.delete()
    tp = TermParent.objects.filter(term__exact=tpk)
    tp.delete()


      
#######################################
## code-level templates
# (Mr. Lazy)
      
def tmpl_instance_message(msg, title):
  return mark_safe('{0} <i>{1}</i>.'.format(msg, html.escape(title)))
  
  
########################################
from django.forms import ModelForm


#########################################

from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

csrf_protect_m = method_decorator(csrf_protect)

from django.contrib import messages
from django.db import models, router, transaction


#-
def _term_delete_action(request, pk):
  
      # whatever we are doing, we need the tree pk
      try:
        t = Term.objects.get(pk__exact=pk)
        treepk = t.tree
      except Term.DoesNotExist:
        # bail out to the main list
        msg = "Term with ID '{0}' doesn't exist. Perhaps it was deleted?".format(
            int(pk)
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('tree-list'))

                     
      if (request.method == 'POST'):
          # delete confirmed          
          Term.system.delete_recursive(pk)

          # cache is invalid
          cache_clear()
    
          msg = tmpl_instance_message("Deleted Term", t.title)
          messages.add_message(request, messages.SUCCESS, msg)
          return HttpResponseRedirect(reverse('term-list', args=[treepk]))

      message = '<p>Are you sure you want to delete the Term "{0}"?</p><p>Deleting a term will delete all its term children if there are any. This action cannot be undone.</p><p>(deleting a term will not delete elements attached to the term)</p>'.format(
        html.escape(t.title)
        )

      context={
        'title': tmpl_instance_message("Delete term", t.title),
        'message': mark_safe(message),
        'submit': {'message':"Yes, I'm sure", 'url': reverse('term-delete', args=[pk])},
        'actions': [link('No, take me back', reverse("term-list", args=[treepk]), attrs={'class':'"button"'})],
      } 
      return render(request, 'taxonomy/delete_confirm_form.html', context)


#@csrf_protect_m        
def term_delete(request, pk):
  # Lock the DB. Found this in admin.
    with transaction.atomic(using=router.db_for_write(Term)):
      return _term_delete_action(request, pk)
  
    
    
##########################################
from .models import Term


#########################
# List of Tree Datas
# Also needs links to terms?

def link(text, href, attrs={}):
  '''
  @param attrs dict of HTML attributes. these are not escaped
  '''
  #NB 'attrs' can not use kwargs because may want to use reserved words
  # for keys, such as 'id' and 'class'
  b = []
  for k,v in attrs.items():
    b.append('{0}={1}'.format(k, v))
  return mark_safe('<a href="{0}" {1}/>{2}</a>'.format(
    html.escape(href),
    ' '.join(b),
    html.escape(text)
    ))
  
class TermListView(TemplateView):
  template_name = "taxonomy/term_list.html"
  

  def get_context_data(self, **kwargs):
      #print('kwargs:')
      #print(str(kwargs))
      treepk=kwargs['treepk']
      td = tree_data(treepk)
      context = super(TermListView, self).get_context_data(**kwargs)

      context['title'] = mark_safe(('Terms in <i>{0}</i>').format(html.escape(td.title)))
      context['tools'] = [link('Add', reverse('term-add', args=[treepk]))]
      context['headers'] = [mark_safe('TITLE'), mark_safe('ACTION')]
      context['messages'] = messages.get_messages(self.request)
      context['navigators'] = [link('Tree List', reverse('tree-list'))]
      #print('context:')
      #print(str(self.request))
      ## form of rows
      # - name with view link
      # - tid parent depth (all hidden)
      # - 'edit' link
      rows = []
      # Term row displays come in two forms...
      if (not td.is_single):
        # multiple can not show the structure of the tree
        # (...it could if it was small, but let's be consistent)
        term_data_queryset = Term.objects.order_by('weight', 'title').filter(tree__exact=treepk).values_list('pk', 'title')
        for e in term_data_queryset:
          rows.append({
            'view': link(e.title, reverse('term-preview', e.pk)),
            'edit': link('edit', reverse('term-edit', e.pk))
          })    
      else:
        # single parentage can show the structure of the tree
        tree = tree_terms_ordered(treepk)
        for e in tree:
          name = term_data(e.pk).title
          #? Unicode nbsp is probably not long-term viable
          # but will do for now?
          title = '\u00A0'*(e.depth*2) + name
          # (extra context data in case we enable templates/JS etc.)
          rows.append({
            'view': link(title, reverse('term-preview', args=[e.pk])),
            'termpk': e.pk,
            'parent': e.parents[0],
            'depth': e.depth,
            'edit': link('edit', reverse('term-edit', args=[e.pk]))
          })
      context['rows'] = rows
      
      return context

################

from django import forms

#class TermSelectWidget(forms.Select):
    #def __init__(self, attrs=None, choices=()):
        #super().__init__(attrs, choices)
        ## choices can be any iterable, but we may need to render this widget
        ## multiple times. Thus, collapse it into a list so it can be consumed
        ## more than once.
        #self.term_data = Terms.objects.all().values_list('pk', 'titles')

    #need a render override        
        
#https://stackoverflow.com/questions/15795869/django-modelform-to-have-a-hidden-input
class TermForm(forms.Form):
    #? can auto-build parameters from the model?
    # prefilled and hidden, in any circumstance
    #treepk = forms.IntegerField(max_value=100, widget=forms.HiddenInput())
    #? cache
    
    # Not a model form field
    # has a placeholding widget
    parents = forms.IntegerField(max_value=100, widget=forms.Select())
    #, widget=forms.Select(choices=current_termdata))

  #???slug field?
    #! how big is the field?
    tree = forms.IntegerField(min_value=0, max_value=32767, widget=forms.HiddenInput())
    title = forms.CharField(label='Title', max_length=64)
    slug = forms.SlugField(label='Slug', max_length=64)
    description = forms.CharField(required= False, label='Description', max_length=255)
    weight = forms.IntegerField(label='Weight', min_value=0, max_value=32767)
    #instance = None
    
    def __init__(self, *args, **kwargs):
      # awkward---pop non-standard data before construction 
      parent_choices=kwargs['initial'].pop('parent_choices')

      super().__init__(*args, **kwargs)
      
      # data is built lazy, thankyou, otherwise we'd never get
      # selected data in there too
      self.fields['parents'].widget.choices=parent_choices

      #? cache
      # get potential parents.
      #treepk = kwargs['initial'].treepk if ('initial' in kwargs) else args[0]['treepk']
      #term_pks = TermTree.objects.filter(taxonomy__exact=self.treepk)
      #current_termdata = Term.objects.filter(pk__in=term_pks).values_list('pk', 'title')
      #print(str(self.fields['parent'].widget))
      #self.fields['parent'].widget.choices=current_termdata
      #print('chain:')
      #for e in tree_term_select_titles(1):
      #  print(str(e))
      #if (not form.bounded):
        # must be request
      #self.fields['parent'].widget.choices=tree_term_select_titles(1)
      # not working...
      #self.fields['parent'].widget.selected=kwargs['initial']['pk']
          
          
# From ModelForm...
def model_to_dict(instance):
    """
    Return a dict containing the data in ``instance`` suitable for passing as
    a Form's ``initial`` keyword argument.

    ``fields`` is an optional list of field names. If provided, return only the
    named.

    ``exclude`` is an optional list of field names. If provided, exclude the
    named from the returned dict, even if they are listed in the ``fields``
    argument.
    """
    opts = instance._meta
    data = {}
    for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        if not getattr(f, 'editable', False):
            continue
        data[f.name] = f.value_from_object(instance)
    return data
  

def tree_pk(termpk):
    try:
      treepk = Tree.objects.get(term__exact=termpk).tree
    except Tree.DoesNotExist:
      raise Http404('The requested admin page does not exist.')
    return treepk

#OK  
def term_add(request, treepk):
    # check the treepk exists
    try:
      Tree.objects.get(pk__exact=treepk)
    except Tree.DoesNotExist:
      raise Http404('The requested admin page does not exist.')
    
    if request.method == 'POST':
        # submitted data, populate
        f = TermForm(
            request.POST,
            initial=dict(parent_choices = tree_term_select_titles(int(treepk)))
            )

        ## check whether it's valid:
        if f.is_valid():

            t = Term.system.create(
                treepk=f.cleaned_data['tree'], 
                parents=f.cleaned_data['parents'],
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
                
            cache_clear()
          
            msg = tmpl_instance_message("Created new Term", f.cleaned_data['title'])
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[treepk]))
            
        else:
            msg = "Please correct the errors below."
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
            
    else:
        # empty form for add
        # set parent to the root (always exists, as an option) 
        f = TermForm(initial=dict(
          tree = treepk,
          weight = 0,
          parent_choices = tree_term_select_titles(int(treepk)),
          parent = -1,
          ))
        
    context={
    'form': f,
    'title': 'Add Term',
    'navigators': [
      link('Term List', reverse('term-list', args=[treepk])),
      ],
    'submit': {'message':"Save", 'url': reverse('term-add', args=[treepk])},
    'actions': [],
    }    

    return render(request, 'taxonomy/generic_form.html', context)


# TemplateView
def term_edit(request, pk):
    # whatever we are doing, we need the tree id
    try:
      treepk = Term.objects.get(pk__exact=pk).tree
      single_parent = Tree.objects.get(pk__exact=treepk).is_single
    except Term.DoesNotExist:
      raise Http404('The requested admin page does not exist.')

    #print('pk:')
    #print(type(pk))
    

    
    
    ## submitted update form
    if request.method == 'POST':
        # create a form instance and validate
        f = TermForm(request.POST,
                initial=dict(parent_choices = tree_term_select_titles(treepk, [int(pk)]))
        )

        if (not f.is_valid()):
            #print('cleaned data:')
            #print(str(f.cleaned_data))
            
            msg = "Term failed to validate?"
            messages.add_message(request, messages.ERROR, msg)
            #? falls through to another render?
        else:
            # valid

            # update parents.
            #! validation of parenting
            #? maybe do on model, or not? 

            #? parent between trees Not Allowed?
            #if (f.fields['treepk'].has_changed()):
            
            # if this is single parent, the only object it cna not be 
            # parented by is itself.
            #! handle mutiple            
            
            t = Term.system.update(
                treepk=f.cleaned_data['tree'], 
                parents=f.cleaned_data['parents'], 
                pk=pk, 
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
            

            # cache now invalid
            cache_clear()
            
            msg = tmpl_instance_message("Updated Term", t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[treepk]))
            

    else:
        # requested update form
        parents = term_parent_pks(treepk, int(pk))

        #if(single_parent):
          # easy, can't be a parent to itself, but all else is ok
        # exclude itself as a paremt, as a basic
        exclude = [int(pk)]
        #else:
          # dont admit a term to be a child of itself or descendants 
          #children = tree_terms_ordered(treepk, parent_pk=int(pk))
          #exclude = term_descendant_pks(treepk)
          #exclude.append(int(pk))
                    
        #get current data manually
        try:
            term = Term.objects.get(pk=pk)
        except Term.DoesNotExist:
          raise Http404('The requested admin page does not exist.')
          
        initial = model_to_dict(term)
        # add in the non-model treepk field inits
        initial['parents'] = parents[0]
        initial['parent_choices'] = tree_term_select_titles(treepk, exclude)

        f = TermForm(initial=initial)
        
        #w = forms.CheckboxSelectMultiple(
          #help_text=u'(Required) 3 days must be selected',
          #choices=tree_term_select_titles(treepk, exclude)
          #)
        #f.fields['parent'].widget = w
        # fix the parent widget
        #f.fields['parent'].widget.choices=tree_term_select_titles(treepk, exclude)

    #if (f.is_bound):
    title = 'Edit term <i>{0}</i>'.format(html.escape(term_data(pk).title))
    #else:
     # title = 'Add term to <i>{0}</i>'.format(html.escape(tree_data(treepk)[0]))
     
    context={
    'form': f,
    'title': mark_safe(title),
    'navigators': [
      link('Tree List', reverse('tree-list')),
      link('Term List', reverse('term-list', args=[treepk]))
      ],
    'submit': {'message':"Save", 'url': reverse('term-edit', args=[pk])},
    'actions': [link('Delete', reverse("term-delete", args=[pk]), attrs={'class':'"button alert"'})],
    }
    
    return render(request, 'taxonomy/generic_form.html', context)

#########################
def _tree_delete(request, pk):

      # The object exists?
      try:
        t = Tree.objects.get(pk__exact=pk)
      except Exception as e:
        # bail out to the main list
        msg = "{0} with ID '{1}' doesn't exist. Perhaps it was deleted?".format(
            'Tree',
            int(pk)
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('tree-list'))


             
      if (request.method == 'POST'):
          # delete confirmed

          Tree.system.delete(int(pk))
          
          # cache is invalid
          cache_clear()
    
          msg = tmpl_instance_message("Deleted tree", t.title)
          messages.add_message(request, messages.SUCCESS, msg)
          return HttpResponseRedirect(reverse('tree-list'))

      else:
          message = '<p>Are you sure you want to delete the Tree "{0}"?</p><p>Deleting a tree will delete all its term children if there are any. This action cannot be undone.</p><p>(deleting a tree will not delete elements attached to the terms)</p>'.format(
              html.escape(t.title)
              )
      
      context={
        'title': tmpl_instance_message("Delete tree", t.title),
        'message': mark_safe(message),
        'submit': {'message':"Yes, I'm sure", 'url': reverse('tree-delete', args=[pk])},
        'actions': [link('No, take me back', reverse("tree-list"), attrs={'class':'"button"'})],
        'model_name': 'Taxonomy',
        'instance_name': html.escape(t.title),
      } 
      return render(request, 'taxonomy/delete_confirm_form.html', context)


#@csrf_protect_m        
def tree_delete(request, pk):
    # Lock the DB. Found this in admin.
    #? lock what? How?
    with transaction.atomic(using=router.db_for_write(Tree)):
      return _tree_delete(request, pk)
      
#########################
# List of Tree Datas
#! Model templates can be merged?
class TreeListView(TemplateView):
  template_name = "taxonomy/tree_list.html"

  def get_context_data(self, **kwargs):
      context = super(TreeListView, self).get_context_data(**kwargs)

      context['title'] = 'Tree List'
      context['tools'] = [link('Add', reverse('tree-add'))]
      context['headers'] = [mark_safe('TITLE'), mark_safe('ACTION'), mark_safe(''), mark_safe('')]
      #context['navigators'] = [mark_safe('<a href="/taxonomy/tree/list"/>tree list</a>')]
      context['messages'] = messages.get_messages(self.request)

      rows = []
      tree_queryset = Tree.objects.order_by('weight', 'title').all().values_list('pk', flat=True)

      for pk in tree_queryset:
          title = tree_data(pk).title
          rows.append({
            'pk': pk,
            'title': title,
            #'weight': e.weight,
            'edit': link('edit', reverse('tree-edit', args=[pk])),
            'list': link('list terms', reverse('term-list', args=[pk])),
            'add': link('add terms', reverse('term-add', args=[pk]))
          })       
      context['rows'] = rows
      
      return context

################
class TreeForm(ModelForm):
    class Meta:
        model = Tree
        fields = ['title', 'slug', 'description', 'is_single', 'is_unique', 'weight']
        

  
#! add 'parent' field
def tree_add(request):
    
    if request.method == 'POST':
        # submitted data, populate
        f = TreeForm(request.POST)
        
        try:
          f.save()
          
          cache_clear_tree()
          msg = tmpl_instance_message("Created new Tree", f.cleaned_data['title'])
          messages.add_message(request, messages.ERROR, msg)
          return HttpResponseRedirect(reverse('tree-list'))
          
        except ValueError:
          msg = "Please correct the errors below."
          messages.add_message(request, messages.ERROR, msg)
          # falls through to another render
    else:
        # empty form for add
        f = TreeForm()
        
    context={
    'form': f,
    'title': 'Add Tree',
    'navigators': [
      link('Tree List', reverse('tree-list')),
      ],
    'submit': {'message':"Save", 'url': reverse('tree-add')},
    'actions': [],
    }    

    return render(request, 'taxonomy/generic_form.html', context)
    
    
def tree_edit(request, pk):
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        #t = Tree.objects.get(pk=pk)
        f = TreeForm(request.POST)
        try:
          # update
          # thows errors if validate fails
          f.save()
          
          # cache is invalid
          cache_clear_tree()
          
          msg = tmpl_instance_message("Update tree", f.cleaned_data['title'])
          messages.add_message(request, messages.SUCCESS, msg)
          return HttpResponseRedirect(reverse('tree-list'))
        except ValueError:
          msg = "Tree failed to validate?"
          messages.add_message(request, messages.ERROR, msg)
    else:
        #? protect
        t = Tree.objects.get(pk=pk)
        f = TreeForm(instance=t)
        
    title = 'Edit tree <i>{0}</i>'.format(html.escape(tree_data(pk).title))
    context={
    'form': f,
    'title': mark_safe(title),
    'action_title': 'Save',
    'navigators': [
      link('Tree List', reverse('tree-list')),
      link('Term List', reverse('term-list', args=[pk]))
      ],
    'submit': {'message':"Save", 'url': reverse('tree-edit', args=[pk])},
    'actions': [link('Delete', reverse("tree-delete", args=[pk]), attrs={'class':'"button alert"'})],
    }

    return render(request, 'taxonomy/generic_form.html', context)
