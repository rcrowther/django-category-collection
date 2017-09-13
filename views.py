from django.shortcuts import render

# Create your views here.

from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.urls import reverse
from django.http import Http404, HttpResponseRedirect
from django.utils import html
from django.utils.safestring import mark_safe
from django.views.decorators.cache import never_cache
from django.db import connection
from itertools import chain
from functools import partial
import sys
from collections import namedtuple

from .models import Term, Tree, TermParent, TermNode




#TODO:
# Some url solution
# how big is that pk field?
# check actions
# check nodes
# check weights
# access methods
# SQL utilities to the model
# have at look at SQL queries
# paginate
# multiparents
# protect form fails
# test permissions admin
# generictemplate module detection
# Tree form not ModelForm
# set weight to zero button
# cache term data using djano, or ok?
# maybe not parent to root when is root?

#######################################################
## data caches

# we cache, so need some module-wide storage.
# pointer to the module object instance
# https://stackoverflow.com/questions/1977362/how-to-create-module-wide-variables-in-python#1978076
this = sys.modules[__name__]


# carrying a full set of terms is covered by Django query caching
# so this may be deprecated. But this can be part-cleared and allows
# record retrieval from cache.
this._tree_cache = {}

def tree(tree_pk):
    '''
    Return a tree from an id.
    
    @param treepk int or int-coercable string 
    @return a Tree, or None
    '''
    if (not this._tree_cache):
        xt = Tree.objects.all()
        for t in xt:
            this._tree_cache[int(t.pk)] = t
        #![this._tree_cache[int(t.pk)] = t for t in xt]
    return this._tree_cache.get(int(tree_pk))



#this._term_data = {}
#TermData = namedtuple('TermData', ['tree', 'title', 'description'])

#def term_data(term_pk):
  #'''
  #data for a given term.
  
  #@param treepk int or int-coercable string 
  #@return TermData named tuple
  #'''
  #pk = int(term_pk)
  #d = this._term_data.get(pk)
  #if (not d):
    #t = Term.objects.get(pk__exact=pk)
    #d = TermData(t.tree, t.title, t.description)
    #this._term_data[pk] = d
  #return d



#def term_treepk(term_pk):
  #'''
  #treepk for a given term pk.
  #Convenience method, but used internally.
  
  #@param treepk int or int-coercable string 
  #@return the pk. Guarenteed int.
  #'''
  #return int(term(term_pk).tree)



#######################################################
## hierarchy cache

# Cache of hierarchial associations
# cache{tree_id: {term_id: [associated_term_ids]}}
this._child_cache = {}
this._parent_cache = {}

# _term_data_cache{tree_id: [{term_id:TermTData...}]}
this._term_data_cache = {}

# storage tuples
TermTData = namedtuple('TermFTData', ['title', 'slug', 'description'])
TermFTData = namedtuple('TermFTData', ['pk', 'title', 'slug', 'description', 'depth'])


def _cache_populate(tree_pk, e):  
    assert isinstance(tree_pk, int), "Not an integer!"

    # data is from raw SQL, needs type assurances  
    term_pk = int(e[0])
    parent_pk = int(e[1])
    if (parent_pk in this._child_cache[tree_pk]):
      this._child_cache[tree_pk][parent_pk].append(term_pk)
    else:
      this._child_cache[tree_pk][parent_pk] = [term_pk]
    if (term in this._parent_cache[tree_pk]):
      this._parent_cache[tree_pk][term_pk].append(parent_pk)
    else:
      this._parent_cache[tree_pk][term_pk] = [parent_pk] 



def _assert_cache(tree_pk):
    '''
    @return True if cache is available, else False 
    '''
    assert isinstance(tree_pk, int), "Not an integer!"
    
    # child cached used as mark for state of other tree cache
    if (tree_pk in this._child_cache):
      return True
    else:
        if (tree(tree_pk) == None):
           return False
        else:
          # ensure we start with -1 kv present, we may look for that
          # as default
          this._child_cache[tree_pk] = {TermParent.NO_PARENT:[]}
          this._parent_cache[tree_pk] = {}
          
          # Python claims to be functional...
          TermParent.system.foreach_ordered(tree_pk, partial(_cache_populate, tree_pk ))
    
          # populate term data
          xt = Term.objects.filter(tree__exact=tree_pk)
          this._term_data_cache[tree_pk] = {
              t.pk : TermTData(t.title, t.slug, t.description) 
              for t in xt
              }
          return True
    
# why the parents? because we can, or is there some use?
#? depth start at 0
#! better max depth
FULL_DEPTH = None
def terms_flat_tree(tree_pk, parent_pk=TermParent.NO_PARENT, max_depth=FULL_DEPTH):
    '''
    Return data from Terms as a flat tree.
    Each item is an TermFTData (pk, title, description, extended with 'depth' and
    'parents' attributes).
    Note that depth starts at 0.
    
    @param tree_pk int or coercable string
    @param parent_pk start from the children of this term. int or coercable string.
    @param max_depth prune the tree beyond this value. Corresponds with
     depth (value 0 will print one row, if data is available, at depth 0) 
    @return list of TermFTData(pk, title, slug, description, depth). None
    if paramerters fail to verify. Empty list if tree has no terms. 
    '''
    treepk = int(tree_pk)
    parentpk = int(parent_pk)

    # cache available?
    if (not  _assert_cache(treepk)):
        return None

    tree = []
    #print('flat t access:')
    #print(str(this._child_cache))
    #print(str(this._parent_cache))
    #print(str(this._term_data_cache))
        
    # unverifiable parentpk?
    if (not ((parentpk in this._parent_cache[treepk]) or (parentpk == TermParent.NO_PARENT))):
          # parentpk either not valid or a leaf, return empty
      return None
         
    # clean access to these caches
    children = this._child_cache[treepk]
    parents = this._parent_cache[treepk]
    term_data = this._term_data_cache[treepk]
    _max_depth =  len(children) if (max_depth == None) else max_depth

    # Stack of levels to process. Each level is an iter.
    # preload with the first set of children
    stack = [iter(children[parentpk])]
    depth = 0
    
    while (stack and depth < _max_depth):
        depth = len(stack)
        it = stack.pop()
    
        while(True):
            try:
                pk = it.__next__()
            except StopIteration:
                # exhausted. Pop another iter at a previous depth
                break
            td = term_data[pk]
            tree.append(TermFTData(pk, td.title, td.slug, td.description, depth))
            child_pks = children.get(pk)
            if (child_pks and depth < _max_depth):
                # append current iter, will return after processing children
                stack.append(it)
                # append new depth of iter
                stack.append(iter(child_pks))
                break
          
    return tree


  
################################################
## Cache clear

def cache_clear_term(treepk):
    '''
    For all term action modifying state.
    Kills the given tree. Empties term data.
  
    @param tree_pk must exist or simple exception
    '''
    # All actions modify the tree, as terms are anchored to them.
    # Term deletion produces a cascading delete, so needs a general
    # reset. 
    this._term_data_cache = {}
    this._child_cache = {}
    this._parent_cache = {}
    #this._tree[int(treepk)] = {}


def cache_clear_term_create_update(tree_pk, term_pk=None):
    '''
    For all term action modifying state.
    Kills the given tree. Deletes term data.
    
    @param tree_pk must exist or simple exception
    @param term_pk must exist or simple exception
    '''
    # All actions modify the tree, as terms are anchored to them.
    # Term deletion produces a cascading delete, so needs a general
    # reset.     
    # if added, or updated after startup, no cache
    if ((not term_pk is None) and (term_pk in this._term_data_cache)):
        del(this._term_data_cache[int(term_pk)])
    this._child_cache = {}
    this._parent_cache = {}
    #this._tree[int(tree_pk)] = {}


  
def cache_clear_tree_create_update():
    '''
    For create or update on a Tree
    Clears tree data. 
    '''
    this._tree_cache = {}


def cache_clear():
    '''
    For tree delete.
    ...or other general purpose.
    '''
    this._tree_cache = {}
    this._term_data_cache = {}
    this._child_cache = {}
    this._parent_cache = {}
    this._tree = {}



########################################
## helpers

# data for:
# term (cache)
# term by name (db)
# tree for term

# ordered by title/weight
# tree (cache)
# list of terms for tree
# list of trees

# parents (taxonomy_get_parents db)
# children (taxonomy_get_children db)
# ancestors of term  (taxonomy_get_parents_all -db)
# descendants of term (drupal -db)

# list of elements for term (taxonomy_select_nodes cache)
#? list of elements for terms
#  list of elements for term descendants
# list of terms for element (taxonomy_node_get_terms_by_vocabulary)

# node count
#? descendant node count (taxonomy_term_count_nodes)



# add elements
# remove elements  


def term(term_pk):
    '''
    Return a term from an id.
    
    @param treepk int or int-coercable string 
    @return a Tree, or None
    '''
    #! return None
    return Term.objects.get(pk__exact==term_pk)

def term_from_title(title):
    '''
    @return list of matching terms. Ordered by weight and then title.
    '''
    return Term.objects.order_by('weight', 'title').filter(title__exact=title)

def term_tree(term):
    '''
    The tree containing this term.
    '''
    #! use SQL to join
    return tree(term.tree)

def tree_term_data(tree_pk):
    '''
    Data from all the terms in a tree.
    
    @return [(pk, name, description)]. Ordered by weight and then title.
    '''
    _assert_cache(tree_pk)
    return this._term_data_cache[tree_pk]

def tree_terms(tree_pk):
    '''
    All the terms in a tree.
    Not usually necessary. Try the cached tree_term_data() method.
    
    @return Ordered by weight and then title.
    '''
    return Terms.objects.order_by('weight', 'title').filter(tree__exact==tree_pk)
      
def trees():
    '''
    @return list of tree objects. Ordered by weight and then title.
    '''
    
    # cache is disordered dict, so SQL
    return Tree.objects.order_by('weight', 'title').all()

def term_parents(term_pk):
    '''
    @return list of term tuples. Ordered by weight and then title.
    '''
    return Term.system.parents_ordered(term_pk)

# ascendors are currently a problem. They have a goof use as breadcrumbs
# but locating terms in cached trees is a problem. The term amy not appear
# in branches of a multiple hierarchy. For now, SQL. 
def term_ancestors(term_pk):
  #? do through cache?
    b = []
    parents = term_parents(term_pk)
    while (parents):
        parent = parents.pop()
        for p in term_parents(parent.pk):
            parents.append(p)
        b.append(parent)
    return b
  
  #?
def ancestor_pks(term_pk=TermParent.NO_PARENT):
    '''
    Find all parent ancestors
    @return list of child ids
    '''
    
    # Works from the SQL queires. Easier than finding when and
    # if tree elements are ancestors.
    tpk = int(term_pk)
    treepk = term(tpk).tree
    _assert_cache(treepk)
    parents = this._parent_cache[treepk]
    
    b = []
    # block on initial sentinel
    if (pk > TermParent.NO_PARENT):
        stack = parents[tpk]
        while (stack):
            tpk = stack.pop()
            # Can drop/stop ascending if hit the no-parent sentinel
            if (tpk > TermParent.NO_PARENT):
                b.append(tpk)
                tpks = parents[tpk]
                for e in tpks:
                    stack.append(e)
      
    return b

#cache?
def term_children(term_pk):
    '''
    @return list of term objects. Ordered by weight and then title.
    '''
    return Term.system.children_ordered(term_pk)

def term_descendants(term_pk):
  # do through cache?
    b = []
    children = term_children(term_pk)
    while (children):
        child = children.pop()
        for c in term_children(child.pk):
            children.append(c)
        b.append(child)
    return b


def term_descendant_pks(pk):
    '''
    Find all descendant pks of a term
    @return list of child ids
    '''
    tree_pk = term(pk).tree
    t = terms_flat_tree(tree_pk, pk)
    return [e.pk for e in t]

def term_element_pks(term_pk):
    '''
    @return list of element pks
    '''
    # static cache taxonomy_node_get_terms
    return TermNode.objects.filter(term__exact=term_pk).values_list('node', flat=True)  

#? def terms_elements(tree_pk, element_pk):

def terms_descendant_element_pks(tree_pk, max_depth=FULL_DEPTH, distinct=False, *term_pks):
    '''
    @return a list of element pks
    '''
    #? duplicates in multi trees
    # Better to get the list, rather than work term by term, only one
    # hit on each DB table.
    xt = []
    for pk in term_pks:
      tree = terms_flat_tree(tree_pk, pk, max_depth=max_depth)
      xt.append([t for t in tree])
    print(str(xt))
    return TermNode.objects.filter(term__in=xt).values('node', flat=True)

 
def element_terms(tree_pk, element_pk):
    '''
    Get terms associated with an element, within a tree.
    
    @return queryset of terms. Ordered by weight and then title.
    '''
    return TermNode.system.element_terms(tree_pk, element_pk)


    
    
this._count = {}
#! expiry?
def term_element_count(term_pk):
    '''
    Count of nodes on a single term
    '''
    termpk = int(term_pk)
    r = this._count.get[termpk]
    if (not r):
      r = TermNode.objects.filter(term__exact=termpk).count()
      this._count[termpk] = r
    return r

def term_descendants_element_count(term_pk):
    count = term_element_count(term_pk)
    for t in term_descendants(term_pk):
      count = count + term_element_count(t)
    return count
  
######################
#-
def tree_term_titles(tree_pk):
  '''
  Get terms in a tree
  @return list of term data tuples (pk, title)
  '''
  return Term.objects.filter(tree__exact=tree_pk).values_list('pk', 'title', 'description')



##############################################
## cache accessors

# probably want term_children? all_term_children?
#! What we need is term/tree cache
#def child_data(termpk):
    #_assert_cache(tree_pk)
    #return [_term_data(pk) for pk in  this._children[treepk]
  
#def parent_data(termpk):
    #_assert_cache(tree_pk)
    #return [_term_data(pk) for pk in  this._parent_cache[treepk]

#-
def term_parent_pks(tree_pk, pk):
    treepk = int(tree_pk)
    _assert_cache(treepk)
    return this._parent_cache[treepk][int(pk)]
  

##############################################
## accessors




def tree_select_titles(tree_pk):
    '''
    All titles from a tree.
    The titles have a representation of structure by indenting with '-'.    
    Intended for single parent select boxes.

    @param tree_pk int or coercable string
    @return [(pk, marked title)...]
    '''
    tree = terms_flat_tree(tree_pk)

    # assert a root item
    b = [(TermParent.NO_PARENT, '<root>')]    
    for e in tree:
        b.append((e.pk, '-'*e.depth + html.escape(e.title)))
  
    return b


def tree_term_select_titles(term_pk):
    '''
    Ancestor titles from a tree.
    The titles have a representation of structure by indenting with '-'.
    Intended for single parent select boxes.

    @param term_pk int or coercable string
    @return list [(pk, title)...]
    '''
    # coercion needed for the test below
    pk = int(term_pk)
    tree_pk = term(pk).tree
    
    # assert a root item
    b = [(TermParent.NO_PARENT, '<root>')]
    
    tree = terms_flat_tree(tree_pk)
  
    # too simple. Needs to continue to a root
    gather = True 
    depth_note = -99
    for t in tree:
      
        # switch gather on if root term
        depth = t.depth

        if (depth <= depth_note):
          gather = True
          depth_note = -99
        if (t.pk == pk):
          gather = False
          depth_note = depth

        if (gather):
            b.append((t.pk, '-' * t.depth + html.escape(t.title)))
    return b



      
#######################################
## code-level templates
# (Mr. Lazy)

def link(text, href, attrs={}):
    '''
    Build HTML for a anchor/link.
    
    @param title escaped
    @param href escaped
    @param attrs dict of HTML attributes. Not escaped
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


# ...when a redirect is troublesome
def tmpl_404_redirect_message(model):
  return 'No {0}s found matching this query.'.format(model._meta.verbose_name)

def tmpl_instance_message(msg, title):
  '''Template for a message or title about an model instance'''
  return mark_safe('{0} <i>{1}</i>.'.format(msg, html.escape(title)))
  

  
########################################
## views

from django.forms import ModelForm

from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

csrf_protect_m = method_decorator(csrf_protect)

from django.contrib import messages
from django.db import models, router, transaction



def _term_delete(request, pk):
  
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
          Term.system.delete_recursive(pk)
          cache_clear_term(treepk)
    
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
      return _term_delete(request, pk)
  



class TermListView(TemplateView):
  template_name = "taxonomy/term_list.html"
  
  def get_context_data(self, **kwargs):
      tree1 = tree(int(kwargs['treepk']))
      if (tree1 == None):
        #? cannt redirect in this view?
        raise Http404(tmpl_404_redirect_message(Tree))   
        
      context = super(TermListView, self).get_context_data(**kwargs)
      context['title'] = tmpl_instance_message("Terms in", tree1.title)
      context['tools'] = [link('Add', reverse('term-add', args=[tree1.pk]))]
      context['headers'] = [mark_safe('TITLE'), mark_safe('ACTION')]
      context['messages'] = messages.get_messages(self.request)
      context['navigators'] = [link('Tree List', reverse('tree-list'))]

      ## form of rows
      # - name with view link
      # - tid parent depth (all hidden)
      # - 'edit' link
      rows = []
      
      # Term row displays come in two forms...
      if (not tree1.is_single):
        # multiple can not show the structure of the tree
        # (...could if the tree is small, but let's be consistent)
        term_data_queryset = Term.objects.order_by('weight', 'title').filter(tree__exact=tree1.pk).values_list('pk', 'title')
        for e in term_data_queryset:
          rows.append({
            'view': link(e.title, reverse('term-preview', e.pk)),
            'edit': link('edit', reverse('term-edit', e.pk))
          })    
      else:
        # single parentage can show the structure of the tree
        ftree = terms_flat_tree(tree1.pk)
        
        for t in ftree: 
          #? Unicode nbsp is probably not long-term viable
          # but will do for now
          title = '\u00A0' * (t.depth*2)  + t.title          
          pk = t.pk
          # (extra context data here in case we enable templates/JS etc.)
          rows.append({
            'view': link(title, reverse('term-preview', args=[pk])),
            'termpk': pk,
            'parent': t.parents[0],
            'depth': t.depth,
            'edit': link('edit', reverse('term-edit', args=[pk]))
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
    parents = forms.IntegerField(max_value=100, widget=forms.Select(),
      help_text="Category above ('root' is top-level)."
      )
    #, widget=forms.Select(choices=current_termdata))

    #! how big is the field?
    tree = forms.IntegerField(min_value=0, max_value=32767, widget=forms.HiddenInput())
    
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
#def model_to_dict(instance):
    #"""
    #Return a dict containing the data in ``instance`` suitable for passing as
    #a Form's ``initial`` keyword argument.

    #``fields`` is an optional list of field names. If provided, return only the
    #named.

    #``exclude`` is an optional list of field names. If provided, exclude the
    #named from the returned dict, even if they are listed in the ``fields``
    #argument.
    #"""
    #opts = instance._meta
    #data = {}
    #for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
        #if not getattr(f, 'editable', False):
            #continue
        #data[f.name] = f.value_from_object(instance)
    #return data
  

def tree_pk(termpk):
    try:
      treepk = Tree.objects.get(term__exact=termpk).tree
    except Tree.DoesNotExist:
      raise Http404('The requested admin page does not exist.')
    return treepk

  
def term_add(request, tree_pk):
  
    # check the treepk exists
    if (tree(tree_pk) == None):
        msg = "Tree with ID '{0}' doesn't exist.".format(
            int(tree_pk)
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('term-list', args=[tree_pk]))
        
    treepk = tree_pk
    
    if request.method == 'POST':
        # submitted data, populate
        f = TermForm(
            request.POST,
            initial=dict(parent_choices = tree_select_titles(treepk))
            )

        ## check whether it's valid:
        if f.is_valid():
            treepk = f.cleaned_data['tree']
            
            t = Term.system.create(
                treepk=treepk, 
                parents=f.cleaned_data['parents'],
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
                
            cache_clear_term_create_update(treepk)
          
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
          parent_choices = tree_select_titles(treepk),
          parent = TermParent.NO_PARENT,
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
def term_edit(request, term_pk):
    try:
      term = Term.objects.get(pk__exact=term_pk)
    except Term.DoesNotExist:
        msg = "Term with ID '{0}' doesn't exist.".format(term_pk)
        messages.add_message(request, messages.WARNING, msg)
        
        # must be tree-list, no tree id to work with 
        return HttpResponseRedirect(reverse('tree-list'))
            
    tree1 = tree(term.tree)

        
    #print('pk:')
    #print(type(pk))

    ## submitted update form
    if request.method == 'POST':
        # create a form instance and validate
        f = TermForm(request.POST,
                initial=dict(parent_choices = tree_term_select_titles(term.pk))
        )

        if (not f.is_valid()):
            #print('cleaned data:')
            #print(str(f.cleaned_data))
            
            msg = "Term failed to validate?"
            messages.add_message(request, messages.ERROR, msg)
            #? falls through to another render?
        else:
            # valid

            #! validate
            # - parent not between trees
            # - parent not child of itself
            #if (f.fields['treepk'].has_changed()):
            #! handle mutiple            
            term = Term.system.update(
                treepk=f.cleaned_data['tree'], 
                parents=f.cleaned_data['parents'], 
                pk=term.pk, 
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
            
            cache_clear_term_create_update(term.tree, term.pk)

            msg = tmpl_instance_message("Updated Term", term.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[term.tree]))
            
    else:
        # requested update form
        #parents = term_parent_pks(treepk, pk)

        #if(tree.is_single):
          # easy, can't be a parent to itself, but all else is ok
        # exclude itself as a paremt, as a basic
        #exclude = [int(pk)]
        #else:
          # dont admit a term to be a child of itself or descendants 
          #children = terms_flat_tree(treepk, parent_pk=int(pk))
          #exclude = term_descendant_pks(treepk)
          #exclude.append(int(pk))
                    
          
        #initial = model_to_dict(term)
        initial = dict(
            tree=term.tree,
            title=term.title,
            slug=term.slug,
            description=term.description,
            weight=term.weight
          )
        # add in the non-model treepk field inits
        #?
        parents = term_parents(term.pk)
        initial['parents'] = parents[0] if (parents) else -1
        initial['parent_choices'] = tree_term_select_titles(term.pk)

        f = TermForm(initial=initial)
        
    context={
    'form': f,
    'title': tmpl_instance_message('Edit term', term.title),
    'navigators': [
      link('Tree List', reverse('tree-list')),
      link('Term List', reverse('term-list', args=[tree1.pk]))
      ],
    'submit': {'message':"Save", 'url': reverse('term-edit', args=[term.pk])},
    'actions': [link('Delete', reverse("term-delete", args=[term.pk]), attrs={'class':'"button alert"'})],
    }
    
    return render(request, 'taxonomy/generic_form.html', context)



#########################
def _tree_delete(request, pk):

      # The object exists?
      try:
        #t = Tree.objects.get(pk__exact=pk)
        t = tree(pk)
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
      tree_queryset = Tree.objects.order_by('weight', 'title').values_list('pk', 'title')

      for t in tree_queryset:
          pk = t[0]
          rows.append({
            'pk': pk,
            'title': t[1],
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
          
          cache_clear_tree_create_update()
          
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
          cache_clear_tree_create_update()
          
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
        
    context={
        'form': f,
        'title': tmpl_instance_message("Edit tree", tree(pk).title),
        'action_title': 'Save',
        'navigators': [
          link('Tree List', reverse('tree-list')),
          link('Term List', reverse('term-list', args=[pk]))
          ],
        'submit': {'message':"Save", 'url': reverse('tree-edit', args=[pk])},
        'actions': [link('Delete', reverse("tree-delete", args=[pk]), attrs={'class':'"button alert"'})],
        }

    return render(request, 'taxonomy/generic_form.html', context)
