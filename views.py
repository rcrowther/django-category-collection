from django.shortcuts import render


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

from .models import Term, Base, TermParent, BaseTerm, Element




# TODO:
# Some url solution
# how big is that pk field?
# bulk add/delete (nodes and terms especially)
# check actions
# check nodes
#x check weights
# access methods
# have at look at SQL queries
# SQL commits and transactions?
# paginate
#x multiparents
#x protect form fails
# test permissions admin
# generictemplate module detection
# set weight to zero button
# maybe not parent to root when is root?
#x treelist is duplicating
#clearup the overcooked js
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

def base(base_pk):
    '''
    Return a base from an id.
    
    @param base_pk int or int-coercable string 
    @return a Base, or None
    '''
    if (not this._tree_cache):
        xt = Base.objects.all()
        for t in xt:
           this._tree_cache[int(t.pk)] = t
    return this._tree_cache.get(int(base_pk))



#######################################################
## hierarchy cache

# Cache of hierarchial associations
# cache{tree_id: {term_id: [associated_term_ids]}}
this._child_cache = {}
this._parent_cache = {}

# _term_data_cache{tree_id: [{term_id:TermTData...}]}
this._term_data_cache = {}

# storage tuples
TermTData = namedtuple('TermFTData', ['pk', 'title', 'slug', 'description'])
TermFTData = namedtuple('TermFTData', ['pk', 'title', 'slug', 'description', 'depth'])


def _cache_populate(base_pk, e):  
    assert isinstance(base_pk, int), "Not an integer!"

    # data is from raw SQL, needs type assurances  
    term_pk = int(e[0])
    parent_pk = int(e[1])
    if (parent_pk in this._child_cache[base_pk]):
      this._child_cache[base_pk][parent_pk].append(term_pk)
    else:
      this._child_cache[base_pk][parent_pk] = [term_pk]
    if (term in this._parent_cache[base_pk]):
      this._parent_cache[base_pk][term_pk].append(parent_pk)
    else:
      this._parent_cache[base_pk][term_pk] = [parent_pk] 


def cache_to_string():
    b = []
    b.append('child_cache:')
    b.append(str(this._child_cache))
    b.append('parent_cache:')
    b.append(str(this._parent_cache))
    return '\n'.join(b)

def tdcache_to_string():
    return 'term_data cache:\n' + str(this._term_data_cache)
    
def _assert_cache(base_pk):
    '''
    @return True if cache is available, else False 
    '''
    assert isinstance(base_pk, int), "Not an integer!"
    
    # child cached used as mark for state of other tree cache
    if (base_pk in this._child_cache):
      return True
    else:
        if (base(base_pk) is None):
            raise ImproperlyConfigured('Cache can not be built because given key invalid: base key:{0}'.format(base_pk))
        else:
          print('build cache...')
          # ensure we start with -1 kv present, we may look for that
          # as default
          this._child_cache[base_pk] = {TermParent.NO_PARENT:[]}
          this._parent_cache[base_pk] = {}
          
          # Python claims to be functional...
          TermParent.system.foreach_ordered(base_pk, partial(_cache_populate, base_pk ))
    
          # populate term data
          xt = BaseTerm.system.ordered(base_pk)
          this._term_data_cache[base_pk] = {t[0] : TermTData(t[0], t[1], t[2], t[3]) for t in xt}
          return True
    
# why the parents? because we can, or is there some use?
#? depth start at 0
#! better max depth
FULL_DEPTH = None
def terms_flat_tree(base_pk, parent_pk=TermParent.NO_PARENT, max_depth=FULL_DEPTH):
    '''
    Return data from Terms as a flat tree.
    Each item is an TermFTData (pk, title, description, extended with 'depth' and
    'parents' attributes).
    Note that depth starts at 0.
    
    @param base_pk int or coercable string
    @param parent_pk start from the children of this term. int or coercable string.
    @param max_depth prune the tree beyond this value. Corresponds with
     depth (value 0 will print one row, if data is available, at depth 0) 
    @return list of TermFTData(pk, title, slug, description, depth). None
    if paramerters fail to verify. Empty list if tree has no terms. 
    '''
    treepk = int(base_pk)
    parentpk = int(parent_pk)

    # cache available?
    if (not _assert_cache(treepk)):
        return None

    tree = []
        
    # unverifiable parentpk?
    if (not ((parentpk in this._parent_cache[treepk]) or (parentpk == TermParent.NO_PARENT))):
        # parentpk either not valid or a leaf,
        raise ImproperlyConfigured('Flat tree can not be built because parent key invalid: Parent key:{0}'.format(parentpk))

    # jump access to these caches
    children = this._child_cache[treepk]
    parents = this._parent_cache[treepk]
    term_data = this._term_data_cache[treepk]
    _max_depth = (len(children) + 1) if (max_depth == None) else max_depth
    #print('build...' + str(_max_depth))

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
            if (child_pks and ((depth + 1) < _max_depth)):
                # append current iter, will return after processing children
                stack.append(it)
                # append new depth of iter
                stack.append(iter(child_pks))
                break
          
    return tree


  
################################################
## Cache clear

def cache_clear_flat_tree(base_pk):
    '''
    Kill the given tree within the flat data cache.
    For actions modifying term state.
  
    @param base_pk must exist or simple exception
    '''
    # Term actions may modify the tree, as terms are anchored to them.
    # Term deletion produces a cascading delete, so needs a general
    # reset. 
    treepk = int(base_pk)
    try:
        # may be empty, if never used...
        #(NB: controller child cache first)
        del(this._child_cache[treepk])
        #del(this._parent_cache[treepk])
        #del(this._term_data_cache[treepk])
    except KeyError:
      # ...don't care.
      pass
  
def cache_clear_tree_cache():
    '''
    Clear cached tree (not flat tree) data. 
    For create or update on a Base. There is no need to touch flat tree
    data for this.
    '''
    this._tree_cache = {}


def cache_clear():
    '''
    Reset all caches.
    *warning* drastic measures only ...or other general purpose.
    '''
    this._tree_cache = {}
    this._term_data_cache = {}
    this._child_cache = {}
    this._parent_cache = {}



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
    Not usually necessary. If you have the tree pk, try term_data().
    
    @param treepk int or int-coercable string 
    @return a Term, or None
    '''
    #! return None
    try:
        return Term.objects.get(pk__exact=term_pk)
    except Term.DoesNotExist:
        return None

def term_data(base_pk, term_pk):
    '''
    Term data.
    From cache.
    
    @return [(pk, name, description)], or None.
    '''
    if (_assert_cache(int(base_pk)) == None):
        return None
    else:
        return this._term_data_cache[int(base_pk)].get(int(term_pk))
  
def term_from_title(title):
    '''
    @return list of matching terms. Ordered by weight and then title.
    '''
    return Term.objects.order_by('weight', 'title').filter(title__exact=title)

def term_tree(term_pk):
    '''
    The tree containing this term pk.
    
    @return the object, or None
    '''
    return Term.system.tree(int(term_pk))

#?-
#def tree_term_data(base_pk):
    #'''
    #Data from all the terms in a tree.
    #From cache. But a disordered hash return.
    
    #@return {pk: (title, slug, description)...} Or None.
    #'''
    #_assert_cache(base_pk)
    #return this._term_data_cache.get[base_pk]

def tree_terms(base_pk):
    '''
    All the terms in a tree.
    
    @return Ordered by weight and then title.
    '''
    return BaseTerm.system.ordered(base_pk)
      
def trees():
    '''
    All Bases.
    
    @return list of tree objects, ordered by weight and then title.
    '''
    # cache is disordered dict, so SQL
    return Base.system.ordered()

def term_parent_data(base_pk, term_pk):
    '''
    From cache.
    @return list of term tuples. Ordered by weight and then title.
    '''
    if (_assert_cache(base_pk) == None):
        return None
    else:
        return this._parent_cache[int(base_pk)].get(int(term_pk))    


def term_child_data(base_pk, term_pk):
    '''
    @return list of term objects. Ordered by weight and then title.
    '''
    if (_assert_cache(base_pk) == None):
        return None
    else:
        return this._child_cache[int(base_pk)].get(int(term_pk)) 

# ascendors are currently a problem. They have a good use as breadcrumbs
# but locating terms in cache is a problem. The term amy not appear
# in branches of a multiple hierarchy. For now, SQL.
# get parents no problem?
def term_ancestor_data(base_pk, term_pk):
    '''
    Return tree-ascending paths of data from Terms.
    Each item in a path is an TermTData (pk, title, slug, description).
    If the hierarchy is multiple, the return may 
    contain several paths/trails. If the hierarcy is single, the 
    function will only return one path.
    Each trail starts at the given termpk and ends at a root. 
    If the paths are used for display purposes, you may wish to reverse() them. 
    
    @param base_pk int or coercable string
    @param child_pk start from the parents of this term. int or coercable string.
    @return list of paths of TermTData(pk, title, slug, description). None
    if parameters fail to verify. Empty list if tree/term_pk has no parents. 
    '''
    if (not _assert_cache(int(base_pk))):
      return None
    else:
      # clean accessors
      parentc = this._parent_cache[int(base_pk)]
      term_data = this._term_data_cache[int(base_pk)]
      
      parents = parentc.get(int(term_pk))
      if (parents == None):
        return None
      else:
        b = []
        trail = []
        trail_stash = [[p] for p in parents]
        #print('trail_stash') 
        #print(str(trail_stash)) 
        while(trail_stash):
            trail = trail_stash.pop()    
            # make current trail
            while(True):
                head = trail[-1]
                #print(str(head))
                if (head == TermParent.NO_PARENT):
                    #completed a trail
                    # pop the delimiting -1 from the trail end.
                    trail.pop()
                    # build data for the pks
                    dt = [term_data[pk] for pk in trail]
                    b.append(dt)
                    break
                parents = parentc[head]
                #parents 1+ put on a copy of the list, then store
                for p in parents[1:]:
                    #print('fork') 
                    #print(str(p)) 
                    trail_stash.append(list.copy(trail).append(p))
                #parent 1 we pursue
                trail.append(parents[0])
        return b
  

def term_ancestor_pks(term_pk):
    '''
    Term ancestor pks.
    @return set of ancestor term pks
    '''
    bpk = BaseTerm.system.base(term_pk)
    _assert_cache(bpk)
    cc = this._parent_cache[bpk]
    b = set()
    base = cc.get(term_pk)
    if (base):
        stack = list(cc[term.pk])
        while (stack):
            tpk = stack.pop()
            if (tpk != TermParent.NO_PARENT):
                parents = cc[tpk]
                for parent in parents:
                    stack.append(parent)
                b.add(tpk)
    return b
    
def term_descendant_pks(term_pk):
    '''
    Term descendant pks.
    @return set of descendant term pks
    '''
    bpk = BaseTerm.system.base(term_pk)
    _assert_cache(bpk)
    cc = this._child_cache[bpk]
    b = set()
    base = cc.get(term_pk)
    if (base):
        stack = list(base)
        while (stack):
            tpk = stack.pop()
            children = cc.get(tpk)
            if (children):
                for child in children:
                    stack.append(child)
            b.add(tpk)
    return b

def base_pks(base_pk):
    '''
    All pks in a tree.
    @return set of descendant term pks
    '''
    _assert_cache(base_pk)
    cc = this._child_cache[base_pk]
    b = set()
    stack = list(cc[TermParent.NO_PARENT])
    while (stack):
        tpk = stack.pop()
        children = cc.get(tpk)
        if (children):
            for child in children:
                stack.append(child)
        b.add(tpk)
    return b  

#def term_descendant_pks(pk):
    #'''
    #Find all descendant pks of a term
    #@return list of child ids
    #'''
    #base_pk = term(pk).tree
    #t = terms_flat_tree(base_pk, pk)
    #if (t == None):
      #return None
    #else:
      #return [e.pk for e in t]
      
def term_element_pks(term_pk):
    '''
    Elements attached to a term.
    @return list of element pks
    '''
    # static cache taxonomy_node_get_terms
    return Element.objects.filter(term__exact=term_pk).values_list('elem', flat=True)  

#? def terms_elements(base_pk, element_pk):

def terms_descendant_element_pks(base_pk, max_depth=FULL_DEPTH, distinct=False, *term_pks):
    '''
    @return a list of element pks. Ordered by term ordering (weight, title).
    '''
    #? duplicates in multi trees
    # Better to get the list, rather than work term by term, only one
    # hit on each DB table.
    xt = []
    for pk in term_pks:
      tree = terms_flat_tree(base_pk, pk, max_depth=max_depth)
      if (tree != None):
        xt.append([t for t in tree])
    #print(str(xt))
    return Element.objects.filter(term__in=xt).values_list('elem', flat=True)

 
def element_terms(base_pk, element_pk):
    '''
    Get terms associated with an element, within a tree.
    
    @return queryset of full terms. Ordered by weight and then title.
    '''
    return Element.system.terms(base_pk, element_pk)


    
    
this._count = {}
#! expiry?
def term_element_count(term_pk):
    '''
    Count of elems on a single term
    '''
    termpk = int(term_pk)
    r = this._count.get[termpk]
    if (not r):
      r = Element.objects.filter(term__exact=termpk).count()
      this._count[termpk] = r
    return r

def term_descendants_element_count(term_pk):
    count = term_element_count(term_pk)
    for t in term_descendants(term_pk):
      count = count + term_element_count(t)
    return count
  
######################
# These two are mainly for admin, to construct selectors and JSON
# Move to a plugin views?


#! term_title_search
def term_title_search(base_pk, pattern=None):
    '''
    Get term pk/titles in a tree
    Case insensitive. 
    @ pattern if given, only titles starting with this pattern are included 
    @return list of term data tuples (pk, title, description)
    '''
    # mainly for JSON admin when choosing terms
    if (pattern is not None):
        return Term.objects.filter(base__exact=base_pk, title__istartswith=pattern).values_list('pk', 'title', 'description')
    else:
        return Term.objects.filter(base__exact=base_pk).values_list('pk', 'title', 'description')

#+
def term_exclusive_select(term):
    '''
    Term data formatted for HTML selectors.
    Term pks from the tree but not a decendent of the given term_pk.
    For parenting terms, to avoid child clashes.
    
    @return list of (pk, title) from a tree which do not descend from, 
    or include, the given term_pk.
    '''
    # This value is mainly for the elimination of child selections when
    # choosing terms (to avoid circular dependencies)
    dpks = term_descendant_pks(term.pk)
    dpks.add(term.pk)
    bpk = BaseTerm.system.base(term.pk)
    ftree = terms_flat_tree(bpk)
    return [(t.pk, ('-' *t.depth) + t.title) for t in ftree if (t.pk not in dpks)]

from django.forms import TypedChoiceField, TypedMultipleChoiceField
#!
def term_form_field_select(base_pk):
    '''
    @return a single or multi-selector field with all-term widget
    '''
        # return differnt kinds of fields depening if this is a 
        # multiparent taxonomy or not
    t = base(base_pk)
    choices = term_choices(base_pk)
    if (t.is_single):
      return TypedChoiceField(
      choices = choices,
      coerce=lambda val: int(val), 
      empty_value=-1,
      label='Taxonomy',
      help_text="Choose a term to parent this item"
      )
    else:
      return TypedMultipleChoiceField(
      choices = choices,
      coerce=lambda val: int(val), 
      empty_value=-1,
      label='Taxonomy',
      help_text="Choose a term to parent this item"
      )
         
##############################################
## cache accessors

# probably want term_children? all_term_children?
#! What we need is term/tree cache
#def child_data(termpk):
    #_assert_cache(base_pk)
    #return [_term_data(pk) for pk in  this._children[treepk]
  
#def parent_data(termpk):
    #_assert_cache(base_pk)
    #return [_term_data(pk) for pk in  this._parent_cache[treepk]

#-
def term_parent_pks(base_pk, pk):
    treepk = int(base_pk)
    _assert_cache(treepk)
    return this._parent_cache[treepk][int(pk)]
  

##############################################
## accessors



#- only a convenience? move?
def tree_select_titles(base_pk):
    '''
    All titles from a tree.
    The titles have a representation of structure by indenting with '-'.    
    Intended for single parent select boxes.

    @param base_pk int or coercable string
    @return [(pk, marked title)...]
    '''
    # can be none
    tree = terms_flat_tree(base_pk)

    # assert a root item
    b = [(TermParent.NO_PARENT, '<root>')]    
    for e in tree:
        b.append((e.pk, '-'*e.depth + html.escape(e.title)))
  
    return b

#-
# used someplace?
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
    base_pk = BaseTerm.system.term(pk).tree
    
    # assert a root item
    b = [(TermParent.NO_PARENT, '<root>')]
    
    #! can be none
    tree = terms_flat_tree(base_pk)
  
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





class TermListView(TemplateView):
  template_name = "taxonomy/term_list.html"
  
  def get_context_data(self, **kwargs):
      tree1 = base(int(kwargs['base_pk']))
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
        term_data_queryset = BaseTerm.system.terms(tree1.pk)
        for o in term_data_queryset:
          pk = o.pk
          rows.append({
            'view': link(o.title, reverse('term-preview', args=[pk])),
            'edit': link('edit', reverse('term-edit', args=[pk]))
          })    
      else:
        # single parentage can show the structure of the tree
            #! can be none

        ftree = terms_flat_tree(tree1.pk)
        
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



################

from django import forms

def _tree_tosingleparent(request, base_pk):
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
          Base.system.is_single(tm.pk, True)
          cache_clear_flat_tree(tm.pk)
          cache_clear_tree_cache()
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
def tree_tosingleparent(request, base_pk):
  # Lock the DB. Found this in admin.
    with transaction.atomic(using=router.db_for_write(TermParent)):
      return _tree_tosingleparent(request, base_pk)
  
  
#######################
## Form helpers

#class TermSelectWidget(forms.Select):
    #def __init__(self, attrs=None, choices=()):
        #super().__init__(attrs, choices)
        ## choices can be any iterable, but we may need to render this widget
        ## multiple times. Thus, collapse it into a list so it can be consumed
        ## more than once.
        #self.term_data = Terms.objects.all().values_list('pk', 'titles')

    #need a render override        
        
#### Elems
#+
def term_choices(base_pk):
    '''
    Term data formatted for HTML selectors.
    Term pks from the tree. For general term parenting.
    
    @return list of (pk, title) from a tree.
    '''
    ftree = terms_flat_tree(base_pk)
    b = [(TermParent.UNPARENT, '<not attached>')]
    [b.append((t.pk, ('-' * t.depth) + t.title)) for t in ftree]
    return b

#+
def term_select_value(base_pk, model_instance):
    '''
    Value to be used in a multiple select button
    @return if instance is none, or a search for existing attached terms
    returns empty, then [TermParent.UNPARENT], else [instance_parent_pk, ...]
    '''
    if (model_instance is None):
        return [TermParent.UNPARENT]
    else:
        xt = element_terms(base_pk, model_instance.pk)
        if (not xt):
            return [TermParent.UNPARENT]
        return [t[0] for t in xt]

def form_set_select(form, taxonomy_field_name, base_pk, instance):
    assert base(base_pk) is not None, "base_pk can not be found: tree_pk:{0}".format(base_pk)
    form.fields[taxonomy_field_name].choices = term_choices(base_pk)
    form.initial[taxonomy_field_name] = term_select_value(base_pk, instance)
        
def element_save(form, taxonomy_field_name, base_pk, obj):
    assert base(base_pk) is not None, "base_pk can not be found: tree_pk:{0}".format(base_pk)
    taxonomy_terms = form.cleaned_data.get(taxonomy_field_name)
    if(taxonomy_terms is None):
        raise KeyError('Unable to find clean data for taxonomy parenting: field_name : {0}'.format(base_pk))
    if ('-2' in taxonomy_terms):
        Element.system.delete(base_pk, obj.pk)
    else:
        Element.system.merge(taxonomy_terms, obj.pk)

def element_remove(base_pk, obj):
    assert base(base_pk) is not None, "base_pk can not be found: tree_pk:{0}".format(base_pk)
    Element.system.delete(base_pk, obj.pk)      

# widget
#- Unused now?
def term_list(base_pk):
    # All titles...
    tree = terms_flat_tree(base_pk)
    #if (tree is None):
    #    raise KeyError('Unable to find tree data: base_pk : {0}'.format(base_pk))
     #! too easy to mix the two items
    # assert an unparent item and a root item
    b = [
        (TermParent.UNPARENT, '<remove from categories>'),    
        (TermParent.NO_PARENT, '<root>')
        ]    
    for e in tree: 
        b.append((e.pk, '-'*e.depth + html.escape(e.title)))
    return b
  
#class TermSelect(forms.Select):
    #def __init__(self, base_pk, attrs=None):
        #print('widget init')
        ##choices=term_list(1)
        ## from ChoiceWidget
        #super().__init__(attrs)

      
       # widget
#class TermSingleSelect(forms.Select):
    #def __init__(self, base_pk, attrs=None):
        #print('   TermSelect widget init')
        ##base_pk, term_pk=None,
        ## All titles...
        ##tree = terms_flat_tree(base_pk)
        #tree = terms_flat_tree(16)
        #if (tree == None):
            #raise KeyError('Unable to find tree data: base_pk : {0}'.format(base_pk))
        ## assert a root item
        #b = [(TermParent.NO_PARENT, '<root>')]    
        #for e in tree: 
            #b.append((e.pk, '-'*e.depth + html.escape(e.title)))
  
        #choices = b
        ##! do some titles?
        #super().__init__(attrs, choices)
       
#class TermMultipleSelect(forms.SelectMultiple):
    #def __init__(self, base_pk, attrs=None):

        #print('   TermSelect widget init')
        ##base_pk, term_pk=None,
        ## All titles...
        ##tree = terms_flat_tree(base_pk)
        #tree = terms_flat_tree(16)
        #if (tree == None):
            #raise KeyError('Unable to find tree data: base_pk : {0}'.format(base_pk))
        ## assert a root item
        #b = [(TermParent.NO_PARENT, '<root>')]    
        #for e in tree: 
            #b.append((e.pk, '-'*e.depth + html.escape(e.title)))
  
        #choices = b
        ##! do some titles?
        #super().__init__(attrs, choices)
        
from django.forms import TypedMultipleChoiceField, MultipleChoiceField
from django.forms.fields import CallableChoiceIterator

#class TermChoiceIterator(CallableChoiceIterator):
#      def __init__(self, base_pk):
#          super().__init__(self, term_list(base_pk))

# Fails to answer several questions
# - is it set to something already?
# - How to react to multi[ple hierarchy?
# - how to act on it? (Element.system.tree_remove(base_pk), Element.system.create(base_pk, element_pk))

class TaxonomyMultipleTermField(forms.TypedMultipleChoiceField):
    def __init__(self, base_pk, *args, **kwargs):
      super().__init__( choices=partial(term_list, base_pk),*args, coerce=lambda val: int(val), **kwargs)

    def valid_value(self, value):
        print('valid value')
        super().valid_value(value)        
       

############################################

#https://stackoverflow.com/questions/15795869/django-modelform-to-have-a-hidden-input
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
    base = forms.IntegerField(min_value=0, widget=forms.HiddenInput())
    
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
      
      base_pk = kwargs['initial']['base']
      tree_model = base(base_pk)
      
      # set form field type
      # default is single parent. If multiple parent, override with
      # multiple-select.
      if(not tree_model.is_single):
          self.fields['parents'] = forms.TypedMultipleChoiceField()
      
      # set choices
      pk = kwargs['initial'].get('pk')
      if(pk is not None):
          # update form. Targeted choices
          #self.fields['parents'].choices = tree_term_select_titles(pk)
          self.fields['parents'].choices = term_exclusive_select(term(pk))
      else:
          # create form. All choices.
          self.fields['parents'].choices = tree_select_titles(base_pk) 

          
  
def term_add(request, base_pk):
    b = base(base_pk)
    if (b == None):
        msg = "Base with ID '{0}' doesn't exist.".format(b.pk)
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('term-list', args=[b.pk]))

    if request.method == 'POST':
        # submitted data, populate
        f = TermForm(request.POST,
            initial=dict(
                      base = b.pk,
                      )
            )

        ## check whether it's valid:
        if f.is_valid():
            t = Term.system.create(
                base_pk=f.cleaned_data['base'], 
                parent_pks=f.cleaned_data['parents'],
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
            
            cache_clear_flat_tree(b.pk)
          
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
          base = b.pk,
          weight = 0,
          # set parents to the root (always exists, as an option) 
          parents = [TermParent.NO_PARENT],
          ))
        
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
            
    b = BaseTerm.system.base(term_pk)
            
    if request.method == 'POST':
        f = TermForm(request.POST,
            initial=dict(
              base = b
              )
        )

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
            t = Term.system.update(
                #treepk=f.cleaned_data['base'], 
                parent_pks=f.cleaned_data['parents'], 
                term_pk=tm.pk, 
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                weight=f.cleaned_data['weight']
                ) 
            
            cache_clear_flat_tree(b)

            msg = tmpl_instance_message("Updated Term", t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[b]))
            
    else:
        # requested update form
        initial = dict(
            base=b,
            # this field triggers modified parent widgets
            pk=tm.pk,
            title=tm.title,
            slug=tm.slug,
            description=tm.description,
            weight=tm.weight
          )
        # add in the non-model treepk field inits
        initial['parents'] = term_parent_data(b, tm.pk)
        f = TermForm(initial=initial)

    context={
    'form': f,
    'title': tmpl_instance_message('Edit term', tm.title),
    'navigators': [
      link('Base List', reverse('base-list')),
      link('Term List', reverse('term-list', args=[b]))
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
          Term.system.delete(tm.pk)
          cache_clear_flat_tree(b)
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
  # Lock the DB. Found this in admin.
    with transaction.atomic(using=router.db_for_write(Term)):
      return _term_delete(request, pk)
  

#########################
# List of Base Datas

      
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
      base_queryset = Base.system.ordered()
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

################
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


#class BaseForm(ModelForm):
    #class Meta:
        #model = Base
        #fields = ['title', 'slug', 'description', 'is_single', 'is_unique', 'weight']
        

  
def tree_add(request):
    if request.method == 'POST':
        f = BaseForm(request.POST)
        if f.is_valid():
            t = Base.system.create(
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                is_single=f.cleaned_data['is_single'],
                weight=f.cleaned_data['weight']
                ) 
            cache_clear_tree_cache()
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
    


def tree_edit(request, base_pk):
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
                
            t = Base.system.update(
                base_pk=tm.pk, 
                title=f.cleaned_data['title'], 
                slug=f.cleaned_data['slug'], 
                description=f.cleaned_data['description'], 
                is_single=f.cleaned_data['is_single'],
                weight=f.cleaned_data['weight']
                ) 
            cache_clear_tree_cache()
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



def _tree_delete(request, base_pk):
      try:
        tm = Base.objects.get(pk__exact=base_pk)
      except Exception as e:
        msg = "{0} with ID '{1}' doesn't exist. Perhaps it was deleted?".format('Base', tm.pk)
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('base-list'))
             
      if (request.method == 'POST'):
          Base.system.delete(tm.pk)
          cache_clear_flat_tree(tm.pk)
          cache_clear_tree_cache()
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
  

#@csrf_protect_m     b   
def tree_delete(request,base_pk):
    # Lock the DB. Found this in admin.
    #? lock what? How?
    with transaction.atomic(using=router.db_for_write(Base)):
      return _tree_delete(request, base_pk)
      

###########################
from .forms import ElementForm

def element_merge(request, term_pk):
    '''
    Associate a pk for a foreign element with a term.
    In english, 'add the id of an item to a category in the trees'.
    Since the id only is used, there is no data to 'update', so this 
    method is called 'merge'. If the id is already attached to the term
    it will not be duplicated.
    '''
    # check the term exists
    try:
        tm = Term.objects.get(pk__exact=term_pk)
    except Term.DoesNotExist:
        msg = "Term with ID '{0}' doesn't exist. Perhaps it was deleted?".format(
            term_pk
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('base-list'))

    if request.method == 'POST':
        # submitted data, populate
        f = ElementForm(request.POST)

        ## check whether it's valid:
        if f.is_valid():
            Element.system.merge(
                term_pk=f.cleaned_data['pk'], 
                element_pk=f.cleaned_data['element']
                ) 
            t = term(f.cleaned_data['pk'])
            msg = tmpl_instance_message("Associated Element Id {0} to Term".format(f.cleaned_data['element']), t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            return HttpResponseRedirect(reverse('term-list', args=[t.tree]))
            
        else:
            msg = "Please correct the errors below."
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
            
    else:
        # empty form for add
        f = ElementForm(initial=dict(
          pk = tm.pk,
          title = tm.title,
          # set parents to the root (always exists, as an option) 
          element = 0,
          ))
        
    context={
    'form': f,
    'title': 'Add Element',
    'navigators': [
      link('Term List', reverse('term-list', args=[tm.tree])),
      ],
    'submit': {'message':"Save", 'url': reverse('element-merge', args=[tm.pk])},
    'actions': [],
    }

    return render(request, 'taxonomy/generic_form.html', context)


def _element_delete(request, base_pk, element_pk):
      try:
        tm = Base.objects.get(pk__exact=base_pk)
      except Base.DoesNotExist:
        msg = "Base with ID '{0}' doesn't exist. Perhaps it was deleted?".format(
            base_pk
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('tree-list'))
        
      xterms = Element.system.tree_element_terms(tm.pk, element_pk)
      if (not xterms):
        msg = "Element with ID '{0}' not attached to any term in Base '{1}'. Perhaps it was deleted?".format(
            element_pk,
            html.escape(tm.title)
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('tree-list'))
        
      if (request.method == 'POST'):
          #Term.system.delete(tm.pk)
          Element.system.tree_remove(tm.pk, element_pk)
          #cache_clear_flat_tree(tm.tree)
          msg = tmpl_instance_message("Deleted element link", element_pk)
          messages.add_message(request, messages.SUCCESS, msg)
          return HttpResponseRedirect(reverse('term-list', args=[tm.pk]))
      else:
          message = '<p>Are you sure you want to delete the element link "{0}" from the tree "{1}"?</p><p>The element is attached to terms named {2}</p>'.format(
            html.escape(element_pk),
            html.escape(tm.title),
            html.escape('"' + '", "'.join([t[1] for t in xterms]) + '"')
            )
          context={
            'title': tmpl_instance_message("Delete element link '{0}' from Base".format(element_pk), tm.title),
            'message': mark_safe(message),
            'submit': {'message':"Yes, I'm sure", 'url': reverse('element-delete', args=[tm.pk, element_pk])},
            'actions': [link('No, take me back', reverse("element-merge", args=[tm.pk]), attrs={'class':'"button"'})],
          } 
          return render(request, 'taxonomy/delete_confirm_form.html', context)


#@csrf_protect_m        
def element_delete(request, base_pk, element_pk):
  # Lock the DB. Found this in admin.
    with transaction.atomic(using=router.db_for_write(Element)):
      return _element_delete(request, base_pk, element_pk)
  
###
#from .forms import ElementSearchForm

#class ElementSearchView(TemplateView):
  #template_name = "taxonomy/generic_form.html"
  
  #def get_context_data(self, **kwargs):
      ##tree1 = tree(int(kwargs['base_pk']))
      ##if (tree1 == None):
        ###? cannt redirect in this view?
        ##raise Http404(tmpl_404_redirect_message(Base))  

      #element_pk = kwargs['element_pk']
      #f = ElementSearchForm(initial=dict(
          #pk = element_pk,
          #title = 'qqq'
          #))
          
      #context = super(ElementSearchView, self).get_context_data(**kwargs)
      #context['form'] = f,
      #context['title'] = 'Link Element',
      #context['navigators'] = [
          #link('Term List', reverse('term-list', args=[1])),
          #],
      #context['submit'] = {'message':html.escape("Save"), 'url': reverse('element-link', args=[element_pk])},
      #context['actions'] = [],

      #return context

import json
from django.http import JsonResponse

#- (merge)
#def term_titles_view(request, base_pk):
    #tl = None
    #if request.method == 'GET':
        #tl = list(tree_term_titles(base_pk))
    #print(str(tl))
    #return JsonResponse(tl, safe=False)
    
    
#http://127.0.0.1:8000/taxonomy/term_titles_ajax/29/
def term_title_search_view(request, base_pk):
    tl = None
    if request.method == 'GET':
        tl = list(term_title_search(base_pk, request.GET.get('search')))
    return JsonResponse(tl, safe=False)



from .fields import IDTitleAutocompleteField
from .widgets import IDTitleAutocompleteInput
from django.core.exceptions import ImproperlyConfigured

    
class ElementSearchForm(forms.Form):
    #pk = forms.IntegerField(label='Element Id', min_value=0,
      #help_text="Id of an element to be categorised."
      #)
      
    title = IDTitleAutocompleteField(
      ajax_href='/taxonomy/term_titles/29',
      label='Element ID/Title', 
      help_text="Title of an element to be categorised."
      )

    def __init__(self, base_pk, *args, **kwargs):
      super().__init__(*args, **kwargs)


#http://127.0.0.1:8000/taxonomy/element/7
def element_link(request, element_pk):
    if request.method == 'POST':
        # create a form instance and validate
        f = ElementSearchForm(request.POST)
        if (not f.is_valid()):
            msg = "Id failed to validate?"
            messages.add_message(request, messages.ERROR, msg)
            # falls through to another render
        else:
            # do something
            t = term(f.cleaned_data['title'])
            msg = tmpl_instance_message("Associated Element Id {0} to Term".format(t), 'noddy')
            messages.add_message(request, messages.SUCCESS, msg)
            #return HttpResponseRedirect(reverse('term-list', args=[t.tree]))
            return HttpResponseRedirect(reverse('element-link', args=[element_pk]))
            
    else:
        # empty form for add
        f = ElementSearchForm(
          initial=dict(
            title = 'z'
          )
        )
        f.fields['title'].widget = IDTitleAutocompleteInput('/taxonomy/term_titles/1')
    print('media')
    print(str(f.media))
    context={
    'form': f,
    'media': f.media,
    'title': 'Add Element',
    'navigators': [
      link('Term List', reverse('term-list', args=[26])),
      ],
    'submit': {'message':"Save", 'url': reverse('element-link', args=[element_pk])},
    'actions': [],
    }
    return render(request, "taxonomy/generic_form.html", context)
