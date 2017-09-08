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

from .models import Term, Tree, TermTree, TermParent

#from blunt_admin.views import ModelAdmin2
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

#class TaxonomyList(ListView):
#  context_object_name = 'taxonomy_list'
#  queryset = Term.objects.filter(parent__isnull=True)

#def taxonomy_list(request):
  #terms = Term.objects.filter(parent__isnull=True)
  #return render(request, 'taxonomy/taxonomy_list.html', {'taxonomy_list' : terms})

##def tree_view(request, slug):
  ##term = Term.objects.get(slug=slug)
  ##if(term.parent):
    ##raise Http404("Tree does not exist")
  ##return render(request, 'taxonomy/term_detail.html', {'term' : term})


#from django import forms

#class TreeListForm(forms.Form):
    #title = forms.CharField(label='title', max_length=100)
    #slug = forms.CharField(label='slug', max_length=100)
    
    
##from .forms import NameForm

#def treelist_view(request):
    ## if this is a POST request we need to process the form data
    #if request.method == 'POST':
        ## create a form instance and populate it with data from the request:
        #form = TreeListForm(request.POST)
        ## check whether it's valid:
        #if form.is_valid():
            ## process the data in form.cleaned_data as required
            ## ...
            ## redirect to a new URL:
            #return HttpResponseRedirect('/thanks/')

    ## if a GET (or any other method) we'll create a blank form
    #else:
        #form = TreeListForm()

    #return render(request, 'taxonomy/tree_list.html', {'form': form})

#from django.contrib.admin import helpers, widgets


#class TreeAddForm(forms.Form):
    #title = forms.CharField(label='title', max_length=100)
    #slug = forms.SlugField(label='slug', max_length=100)
    #is_single = forms.BooleanField(label='is single')
    #is_unique = forms.BooleanField(label='is unique')
    ##weight = forms.IntegerField(label='weight', max_value=3000, min_value=0, max_length=30)
    #weight = forms.IntegerField(label='weight')

#def treeadd_view(request):
    ## if this is a POST request we need to process the form data
    #if request.method == 'POST':
        ## create a form instance and populate it with data from the request:
        #form = TreeAddForm(request.POST)
        ## check whether it's valid:
        #if form.is_valid():
            ## process the data in form.cleaned_data as required
            ## ...
            ## redirect to a new URL:
            #return HttpResponseRedirect('/thanks/')

    ## if a GET (or any other method) we'll create a blank form
    #else:
        #form = TreeAddForm()

    #return render(request, 'taxonomy/tree_add.html', {'form': form})

########################################
## helpers

  
def tree_terms_for_element(tree_pk, pk):
  '''
  Get associated terms
  Ordered by weight.
  @return queryset of terms
  '''
  term_for_tree_ids = TermTree.objects.filter(tree__exact=tree_pk).values_list('term', flat=True)
  term_ids = TermNode.objects.filter(node__exact=pk, term__in=term_for_tree_ids).values_list('term', flat=True)
  return Term.objects.order_by('weight').filter(pk__exact=term_ids)


def tree_term_titles(tree_pk):
  '''
  Get terms in a tree
  @return list of term data tuples (pk, title)
  '''
  term_pks = TermTree.objects.filter(tree__exact=tree_pk)
  return Term.objects.filter(pk__in=term_pks).values_list('pk', 'title')


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
    t = Tree.objects.get(pk__exact=treepk)
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

#def term_children_pk(termpk):

#def term_parents_pk(termpk):
  
def parents(treepk):
  return _parents[treepk]

TermFTData = namedtuple('TermFTData', ['pk', 'depth', 'parents'])
    
#? rename terms_flat_tree?
def tree_terms_ordered(tree_pk, parent_pk=TermParent.NO_PARENT, max_depth=None):
  '''
  Get terms in a tree
  @return list of tuples (termpk, depth. [parent_ids]). Root ids will be parented by [-1].
  '''
  cached = _children.get(tree_pk)
  if (not cached):
    term_pks = TermTree.objects.order_by('weight', 'title').filter(tree__exact=tree_pk)
    term_parents = TermParent.objects.filter(term__in=term_pks)
    _children[tree_pk] = {}
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
  _max_depth = max_depth if max_depth else len(children)
  tree = []

  # Keeps track of the parents we have to process, the last entry is used
  # for the next processing step.
  child_pks = children[parent_pk]
  #
  stack = [iter(child_pks)]

  while stack:
    #! depth counting from 1? Think I prefer 0?
    depth = len(stack)
    it = stack.pop()

    while(True):
      try:
        pk = it.__next__()
      except StopIteration:
        break
      tree.append(TermFTData(pk, depth, parents[pk]))
      
      child_pks = children.get(pk)
      ## check for children
      # only continue down if not exceeded the depth and children exist
      if (depth < _max_depth and child_pks):
        # append current iter, to go back to
        stack.append(it)
        # append new depth of iter
        stack.append(iter(child_pks))
        break
        
  return tree
  
  
def term_node_count(termpk):
  return TermNode.objects.filter(term__exact=termpk).count()

#! filter for illegal where?  
def tree_term_select_titles(tree_pk, exclude=[]):
  tree = tree_terms_ordered(tree_pk)
  b = []
  for e in tree:
    if (not e in exclude):
      name = html.escape(term_data(e.pk).title)
      b.append((e.pk, '-'*e.depth + name))
    
  return b
  #list(chain([(TermParent.NO_PARENT, 'root')], tree_term_titles(tree_pk)))

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
    
    # cache is invalid
    cache_clear()

      
########################################
from django.forms import ModelForm


#########################################

from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

csrf_protect_m = method_decorator(csrf_protect)

from django.contrib import messages
from django.db import models, router, transaction
from django.contrib.admin.utils import quote, unquote


        
def _term_delete_action(request, pk):
      app_label = Term._meta.app_label
      verbose_name = Term._meta.verbose_name

      # The object exists?
      try:
        o = Term.objects.get(pk__exact=pk)
      except Exception as e:
        # bail out to the main list
        msg = "{0} with ID '{1}' doesn't exist. Perhaps it was deleted?".format(
            Term._meta.verbose_name,
            unquote(pk)
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('tree-list'))

      # retrieve the treepk
      # Passing the value through a form means using the template,
      # which is no fun.
      # This horrible retrieval may only be temporary. May remove
      # Django automanagement of the join tables?
      tt = None
      try:
        tt=TermTree.objects.get(term__exact=pk)
      except Exception as e:
        msg = "{0} for Term ID '{1}' is not registered? The database may not be coherent!".format(
            Tree._meta.verbose_name,
            unquote(pk)
        )
        messages.add_message(request, messages.ERROR, msg)
        return HttpResponseRedirect(reverse('tree-list'))
        
      treepk=tt.tree.pk
                     
      if (request.method == 'POST'):
          # delete confirmed
          #! Should delete children too

          #print(str(treepk))
          #raise Exception
          
          #? logging
          #! deletion of descendants
          #o.delete()
          #? model delete cascades seem to delete other table data for us.
          #tt = TermTree(taxonomy=tree, term=term)
          #tt.delete()
          #th = TermParent.objects.filter(term__exact=pk)
          #th.delete()
          _term_delete(pk)
          
          msg = 'The {0} "{1}" was deleted'.format(verbose_name, o.title)
          messages.add_message(request, messages.SUCCESS, msg)
          redirect_url = reverse('term-list', args=[treepk])
          return HttpResponseRedirect(redirect_url)

      message = '<p>Are you sure you want to delete the Term "{0}"?</p><p>Deleting a term will delete all its term children if there are any. This action cannot be undone.</p><p>(deleting a term will not delete elements attached to the term)</p>'.format(
      html.escape(o.title)
      )
      
      context={
        'title': 'Term Delete',
        'html_title': 'term_delete',
        'message': mark_safe(message),
        'submit': {'message':"Yes, I'm sure", 'url': '/taxonomy/term/{0}/delete/'.format(pk)},
        'actions': [mark_safe('<a href="/taxonomy/tree/{0}/term/list" class="button">No, take me back</a>'.format(treepk))],
        'model_name': 'Term',
        'instance_name': html.escape(o.title),
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
  @param attrs not escaped
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
        term_id_queryset = TermTree.objects.filter(tree__exact=context['treepk']).values_list('term', flat=True)
        term_data_queryset = Term.objects.filter(pk__in=term_id_queryset).values_list('pk', 'title')
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
          #? Use unicode nbsp is probably not long-term viable
          # but will do for now?
          title = '\u00A0'*(e.depth*2) + name
          # (extra context gear in case we ever enable templates/JS etc.)
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


#! needs a tree? 
#class TermForm(ModelForm):
    ## need extra field for parent....
    ## and handle the treepk?
    #class Meta:
        #model = Term
        #fields = ['title', 'slug', 'weight']

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
    treepk = forms.IntegerField(max_value=100, widget=forms.HiddenInput())
    #? cache
    parent = forms.IntegerField(max_value=100, widget=forms.Select())
    #, widget=forms.Select(choices=current_termdata))

  #???slug field?
    title = forms.CharField(label='Title', max_length=64)
    slug = forms.SlugField(label='Slug', max_length=64)
    weight = forms.IntegerField(label='Weight', min_value=0, max_value=32767)
    #instance = None
    
    def __init__(self, *args, **kwargs):
      #if ('instance' in kwargs):
        #term = kwargs.pop('instance')
        #kwargs['initial'] = self.model_to_dict(term)
        
      super().__init__(*args, **kwargs)
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
      self.fields['parent'].widget.choices=tree_term_select_titles(1)
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
  


def term_add(request, treepk):
    url_base = '/taxonomy/term/'
  
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = TermForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            # URL base not working?
            #print( str(form.cleaned_data))
          #try:
            print(str(form.cleaned_data))
            
            #! catch repeated terms?
            #! catch circular references?
            
            # get the validated data
            d = form.cleaned_data.copy()
            
            # remove our extra form items
            treepk = d.pop('treepk')
            parentpk = d.pop('parent')
            print('treepk, parent:')
            print(str(treepk))
            print(str(parentpk))
            #Term(slug= 'walks', title= 'walks', weight= 1)

            #! Shambolic, expensive query and writing?
            term = Term(**d)            
            term.save()
            tree=Tree.objects.get(pk=treepk)
            #print('newid:')
            #print(new_pk)
            tt = TermTree(tree=tree, term=term)
            tt.save()
            # handle the 'set to null' problem (parentpk = 0)
            #! handle multiple parents
            #parentpk = parentpk if (parentpk > 0) else None
            th = TermParent(term=term.pk, parent=parentpk)
            th.save()
            #            order = form.save(commit=false)
            # cache now invalid
            cache_clear()
            return HttpResponseRedirect(reverse('term-list', args=[treepk]))
        else:
          #? do what?, see edit?
          raise Http404("Term failed to validate")  
    else:
        # unbound
        # but bind with treepk... but this produces errors?
        #form = TermForm({'treepk': treepk})
        form = TermForm(initial={'treepk': treepk, 'weight': 0})
        #form = TermForm(treepk=treepk)
        context={
        'form': form,
        'title': 'Term Add',
        'html_title': 'term_add',
        'action': '/taxonomy/tree/{0}/term/add/'.format(treepk),
        'action_title': 'Save',
        }    
    return render(request, 'taxonomy/generic_form.html', {'context': context})
    
    
# TemplateView
def term_edit(request, pk):

    #treepk = TermTree.objects.get(term__exact=pk).tree
    treepk = TermTree.objects.get(term__exact=pk).tree.pk
        
    ## if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and validate
        #t = Term.objects.get(pk=pk)
        #initial = model_to_dict(t)

        #f = TermForm(request.POST, initial=initial)
        f = TermForm(request.POST)
        #try:

        if (not f.is_valid()):
            #print('cleaned data:')
            #print(str(f.cleaned_data))
            
            msg = "Term failed to validate?"
            messages.add_message(request, messages.ERROR, msg)
            #? falls through to another render?
        else:
            # valid

            
            # update the object
            t=Term(
              title=f.cleaned_data['title'],
              slug=f.cleaned_data['slug'],
              weight=f.cleaned_data['weight'],
              )
            t.save()
            
            # Should use this? Not changed...
            new_pk = t.pk
            treepk = f.cleaned_data['treepk']
            #? parent between trees Not Allowed?
            #if (f.fields['treepk'].has_changed()):

            #if (f.fields['parent'].has_changed()):
            print('POST')
            print(str(f.initial))
            
            # fix parents. 
            # may not be efficient, but easier to do this wether changed
            # or not, otherwise must compare two potential sets of
            # parents, and do read/write anyhow
            delete_set = TermTree.objects.filter(term__exact=new_pk)
            delete_set.delete()

            tree = Tree.objects.get(pk__exact=treepk)
              
            o = TermTree(
              term=t,
              tree=tree,
              )
            o.save()

            # cache now invalid
            cache_clear_on_update()
            
            msg = 'Term "{0}" was updated'.format(t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect('/taxonomy/tree/{0}/term/list'.format(treepk))
            
        #except ValueError:
        #  raise Http404("Term data failed to update")          


    else:
        # get the object
        #? protect
        term = Term.objects.get(pk=pk)
        initial = model_to_dict(term)
        initial['treepk'] = treepk
        f = TermForm(initial=initial)
        
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
      #? into is all similar - DRY
      #? Post is different
      app_label = Tree._meta.app_label
      verbose_name = Tree._meta.verbose_name

      
      # The object exists?
      try:
        o = Tree.objects.get(pk__exact=pk)
      except Exception as e:
        # bail out to the main list
        msg = "{0} with ID '{1}' doesn't exist. Perhaps it was deleted?".format(
            'Tree',
            unquote(pk)
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('tree-list'))


             
      if (request.method == 'POST'):
          # delete confirmed
                    
          #print(str(treepk))
          #raise Exception
          
          #? logging
          # deletion...
          # ...tree
          o.delete()
          
          # ...term associations
          term_ids = TermTree.objects.filter(tree__exact=pk)
          #, term=term)
          term_ids.delete()
          
          # ...term hierarchy
          #? no need to check parents too
          tree_hierarchy = TermParent.objects.filter(term__in=term_ids)
          tree_hierarchy.delete()
          
          # ...terms
          terms = Term.objects.filter(pk__in=term_ids)
          terms.delete()
          
          # cache is invalid
          cache_clear()
    
          msg = 'The {0} "{1}" was deleted'.format(verbose_name, o.title)
          messages.add_message(request, messages.SUCCESS, msg)
          redirect_url = reverse('tree-list')
          return HttpResponseRedirect(redirect_url)

      message = '<p>Are you sure you want to delete the Tree "{0}"?</p><p>Deleting a tree will delete all its term children if there are any. This action cannot be undone.</p><p>(deleting a tree will not delete elements attached to the terms)</p>'.format(
      html.escape(o.title)
      )
      
      context={
        'title': 'Tree Delete',
        'html_title': 'tree_delete',
        'message': mark_safe(message),
        'submit': {'message':"Yes, I'm sure", 'url': '/taxonomy/tree/{0}/delete/'.format(pk)},
        'actions': [mark_safe('<a href="/taxonomy/tree/list" class="button">No, take me back</a>')],
        'model_name': 'Taxonomy',
        'instance_name': html.escape(o.title),
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
      tree_queryset = Tree.objects.all().order_by('weight', 'title').values_list('pk', flat=True)

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
        fields = ['title', 'slug', 'is_single', 'is_unique', 'weight']
        

#! add 'parent' field
def tree_add(request):
    
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        #form = TermForm(request.POST)
        # check whether it's valid:
        #if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            # URL base not working?
            #print( str(form.cleaned_data))
        f = TreeForm(request.POST)
        try:
          f.save()
          
          # cache is invalid
          cache_clear_tree()
          
          return HttpResponseRedirect(reverse('tree-list'))
        except ValueError:
          #raise Http404("Tree failed to validate")  
          msg = "Tree failed to validate?"
          messages.add_message(request, messages.ERROR, msg)
          #? falls through to another render?
    else:
        f = TreeForm()
    context={
    'form': f,
    'title': 'Tree Add',
    'html_title': 'tree_add',
    'action': '/taxonomy/tree/add/',
    'action_title': 'Save',
    }    
    return render(request, 'taxonomy/generic_form.html', {'context': context})
    
    
def tree_edit(request, pk):
    url_base = '/taxonomy/tree/{0}'.format(pk)
    ## if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        a = Tree.objects.get(pk=pk)
        f = TreeForm(request.POST, instance=a)
        try:
          # update
          # thows errors if validate dails
          f.save()
          
          # cache is invalid
          cache_clear_tree()
          
          msg = 'Tree "{0}" was updated'.format(f.cleaned_data['title'])
          messages.add_message(request, messages.SUCCESS, msg)
          return HttpResponseRedirect(reverse('tree-list'))
        except ValueError:
          msg = "Tree failed to validate?"
          messages.add_message(request, messages.ERROR, msg)
    # if a GET (or any other method) we'll create a blank form
    else:
        #? protect
        o = Tree.objects.get(pk=pk)
        f = TreeForm(instance=o)
        
    context={
    'form': f,
    'title': 'Tree Edit',
    'html_title': 'tree_edit|' + str(pk),
    'action': url_base + '/edit/',
    'action_title': 'Save',
    'navigators': [
      mark_safe('<a href="/taxonomy/tree/list"/>tree list</a>'),
      mark_safe('<a href="/taxonomy/tree/{0}/term/list"/>term list</a>'.format(pk))
      ],
    }
    
    return render(request, 'taxonomy/generic_form.html', {'context': context})
