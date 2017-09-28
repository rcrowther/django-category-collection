
from .models import Term, Base, TermParent, BaseTerm
import sys
from collections import namedtuple
from functools import partial

#! are pk versions necessary?
#! derive base from term or insist on supply?

# Pointer to the module object instance, for module-wide storage.
# https://stackoverflow.com/questions/1977362/how-to-create-module-wide-variables-in-python#1978076
this = sys.modules[__name__]

this._base_cache = {}

def base(base_pk):
    '''
    base from a pk.
    
    @param base_pk int or int-coercable string 
    @return a Base, or None
    '''
    if (not this._base_cache):
        xt = Base.objects.all()
        for t in xt:
           this._base_cache[int(t.pk)] = t
    return this._base_cache[int(base_pk)]



# cache of hierarchial associations
# {tree_id: {term_id: [associated_term_ids]}}
this._child_cache = {}
this._parent_cache = {}

# cache of term data
# {tree_id: [{term_id:Term...}]}
this._term_cache = {}

# cache of term counts
# {term_id: count}
this._count = {}

# storage tuple
TermFTData = namedtuple('TermFTData', ['pk', 'title', 'slug', 'description', 'depth'])


def _cache_populate(base_pk, e):  
    assert isinstance(base_pk, int), "Not an integer!"
    term_pk = int(e[0])
    parent_pk = int(e[1])
    if (parent_pk in this._child_cache[base_pk]):
      this._child_cache[base_pk][parent_pk].append(term_pk)
    else:
      this._child_cache[base_pk][parent_pk] = [term_pk]
    if (term_pk in this._parent_cache[base_pk]):
      this._parent_cache[base_pk][term_pk].append(parent_pk)
    else:
      this._parent_cache[base_pk][term_pk] = [parent_pk] 


def to_str():
    b = []
    b.append('child_cache:')
    b.append(str(this._child_cache))
    b.append('parent_cache:')
    b.append(str(this._parent_cache))
    b.append('term_data cache:')
    b.append(str(this._term_cache))
    return '\n'.join(b)


def _assert_cache(base_pk):
    '''
    Assert cache exists, if not, build it.
    '''      
    assert isinstance(base_pk, int), "Not an integer!"
    
    # child cache used as mark for state of other tree cache
    if (base_pk not in this._child_cache):
        # must come from the databse, not cache :)
        # made runtime check, not assert, as all kinds of user
        # interaction ay make it's way here
        try:
            Base.objects.get(pk__exact=base_pk)
        except Base.DoesNotExist:
            raise KeyError('Cache can not be built because no base exists for given key: base key:{0}'.format(base_pk))
        else:
          # ensure we start with TermParent.NO_PARENT kv present, we may
          # look for that as default
          this._child_cache[base_pk] = {TermParent.NO_PARENT:[]}
          this._parent_cache[base_pk] = {}

          # populate parent data          
          for h in TermParent.system.iter_ordered(base_pk):
              _cache_populate(base_pk, h)
              
          # populate term data
          this._term_cache[base_pk] = {}
          tc = this._term_cache[base_pk]
          for t in BaseTerm.system.term_iter(base_pk):
              tc[t.pk] = t
    

FULL_DEPTH = None
def terms_flat_tree(base_pk, parent_pk=TermParent.NO_PARENT, max_depth=FULL_DEPTH):
    '''
    Return data from Terms as a flat tree.
    Each item is an TermFTData, which is term data extended with a
    'depth' attribute  (pk, title, description, depth). The depth value
    is from the given parent (not the tree top, unless the tree root
    is specified as parent). Since depth 0 is the parent, if any rows
    appear in the output, the depths will start at 1.
    
    @param base_pk int or coercable string
    @param parent_pk start from the children of this term. int or coercable string.
    @param max_depth prune the tree beyond this value. Corresponds with
     depth (0 will return an empty list, 1 will return reows from depth 1, ...) 
    @return list of TermFTData(pk, title, slug, description, depth).
    Empty list if tree has no terms, max_depth = 0 etc.. 
    '''
    basepk = int(base_pk)
    parentpk = int(parent_pk)
    tree = []

    _assert_cache(basepk)
    
    # not good configuration
    if (not ((parentpk in this._term_cache[basepk]) or (parentpk == TermParent.NO_PARENT))):
        raise KeyError('Flat tree can not be returned because given parent key not in the base: parent key:{0}'.format(parentpk))
        
    # jump access to these caches
    children = this._child_cache[basepk]
    parents = this._parent_cache[basepk]
    term_data = this._term_cache[basepk]
    _max_depth = (len(children) + 1) if (max_depth is None) else max_depth
    if ((_max_depth < 1) or (parentpk not in children)):
        # if depth == 0 this is an empty list. Also...
        # if exists but has no children, must be a leaf
        return []
        
    # Stack of levels to process. Each level is an iter.
    # preload with the first set of children
    stack = [iter(children[parentpk])]
    depth = 0
    while (stack):
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
            if (child_pks and (depth < _max_depth)):
                # append current iter, will return after processing children
                stack.append(it)
                # append new depth of iter
                stack.append(iter(child_pks))
                break
    return tree



def base_merge_clear():
    '''
    Clear cached data on base create or update. 
    For create or update on a Base. There is no need to touch other
    data for this.
    '''
    this._base_cache = {}

def base_delete_clear(base_pk):
    '''
    Clear cached data on base delete.
    '''
    assert isinstance(base_pk, int), "Not an integer!"
    this._base_cache = {}
    try:
        del(this._child_cache[base_pk])
    except KeyError:
      pass
    # demolition, unless we recover deleted terms?
    this._count = {}

def term_merge_clear(base_pk):
    '''
    Clear cached data on term create or update. 
    Tree info needs invalidating.
    '''
    assert isinstance(base_pk, int), "Not an integer!"
    try:
        del(this._child_cache[base_pk])
    except KeyError:
      pass
    #N.B. the count will update itself

def term_delete_clear(term_pk):
    '''
    Clear cached data on term delete. 
    Term delete causes recursive deletion, so all base info needs 
    invalidating.
    '''
    assert isinstance(term_pk, int), "Not an integer!"
    base_pk = BaseTerm.system.base(term_pk)
    try:
        del(this._child_cache[base_pk])
        del(this._count[term_pk])
    except KeyError:
      pass
      
def element_merge_clear():
    # demolition, as it will remove from anyplace
    this._count = {}

def element_remove_clear():
    # demolition, as it can remove from anyplace
    this._count = {}
    
def clear():
    '''
    Reset all caches.
    *hint* drastic measures ...or general purpose.
    '''
    this._base_cache = {}
    this._term_cache = {}
    this._child_cache = {}
    this._parent_cache = {}
    this._count = {}

def term(base_pk, term_pk):
    '''
    Term from a pk.
    From cache.
    
    @param base_pk int or int-coercable string 
    @param term_pk int or int-coercable string 
    @return a term.
    '''
    basepk = int(base_pk)
    _assert_cache(base_pk)
    return this._term_cache[base_pk][int(term_pk)]

def term_parent_pks(base_pk, term_pk):
    '''
    From cache.
    @return list of term  pks. Ordered by weight and then title.
    '''
    basepk = int(base_pk)
    _assert_cache(basepk)
    return this._parent_cache[basepk][int(term_pk)]   

def term_parents(base_pk, term_pk):
    '''
    From cache.
    @return list of terms. Ordered by weight and then title.
    '''
    pks = term_parent_pks(base_pk, term_pk)
    return [this._term_cache[int(base_pk)][pk] for pk in pks]
  
def term_child_pks(base_pk, term_pk):
    '''
    From cache.
    @return list of term  pks. Ordered by weight and then title.
    '''
    basepk = int(base_pk)
    _assert_cache(basepk)
    return this._child_cache[basepk][int(term_pk)]   

def term_children(base_pk, term_pk):
    '''
    @return list of term objects. Ordered by weight and then title.
    ''' 
    pks = term_child_pks(base_pk, term_pk)
    return [this._term_cache[int(base_pk)][pk]  for pk in pks]

def term_ancestor_paths(base_pk, term_pk):
    '''
    Return tree-ascending paths of data from Terms.
    If the hierarchy is multiple, the return may contain several 
    paths/trails. If the hierarcy is single, the function will only
    return one path. Each trail starts at the given term_pk and ends at
    a root. If the paths are used for display purposes, you may wish to
    reverse() them. 
    
    @param base_pk int or coercable string
    @param term_pk start from the parents of this term. int or coercable string.
    @return list of lists (paths) of terms. Empty list if term_pk has no parents. 
    '''
    basepk = int(base_pk)
    _assert_cache(basepk)

    # clean accessors
    parentc = this._parent_cache[basepk]
    term_data = this._term_cache[basepk]
    
    parents = parentc.get(int(term_pk))
    if (parents is None):
        return []
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
              # parents[1:] stash a copy of the list with new head
              for p in parents[1:]:
                  #print('fork') 
                  #print(str(p)) 
                  trail_stash.append(list.copy(trail).append(p))
              # parent[0] we pursue
              trail.append(parents[0])
      return b

def term_descendant_paths(base_pk, term_pk):
    '''
    Return tree-descending paths of data from Terms.
    If the hierarchy is multiple, the return may contain several 
    paths/trails. If the hierarcy is single, the function will only
    return one path. Each trail starts at the given term_pk and ends at
    a root. If the paths are used for display purposes, you may wish to
    reverse() them. 
    
    @param base_pk int or coercable string
    @param term_pk start from the parents of this term. int or coercable string.
    @return list of lists (paths) of terms. Empty list if term_pk has no parents. 
    '''
    basepk = int(base_pk)
    _assert_cache(basepk)

    # clean accessors
    childc = this._child_cache[basepk]
    termc = this._term_cache[basepk]
    
    children = childc.get(int(term_pk))
    if (children is None):
        return []
    else:
      b = []
      trail = []
      trail_stash = [[p] for p in children]
      while(trail_stash):
          trail = trail_stash.pop()    
          # make current trail
          while(True):
              head = trail[-1]
              children = childc.get(head)
              if (children is None):
                  # completed a trail
                  # build data for the pks
                  dt = [termc[pk] for pk in trail]
                  b.append(dt)
                  break
              # children[1:]; stash a copy of the list with new head
              for p in children[1:]:
                  trail_stash.append(list.copy(trail).append(p))
              # child[0] we pursue
              trail.append(children[0])
      return b  

def term_ancestor_pks(base_pk, term_pk):
    '''
    Term ancestor pks.
    No duplicate data in the return set. No useful ordering.
    @return set of ancestor term pks
    '''
    assert isinstance(base_pk, int), "Not an integer!"
    assert isinstance(term_pk, int), "Not an integer!"
    _assert_cache(base_pk)
    pc = this._parent_cache[base_pk]
    b = set()
    stack = pc.get(term_pk)
    if (stack):
        stack = list(pc[term_pk])
        while (stack):
            tpk = stack.pop()
            if (tpk != TermParent.NO_PARENT):
                parents = pc[tpk]
                for parent in parents:
                    stack.append(parent)
                b.add(tpk)
    return b
    
#? Not work with -1, because not guess the base?
def term_descendant_pks(base_pk, term_pk):
    '''
    Term descendant pks.
    No duplicate data in the return set. No useful ordering.
    @return set of descendant term pks
    '''
    assert isinstance(base_pk, int), "Not an integer!"
    assert isinstance(term_pk, int), "Not an integer!"
    _assert_cache(base_pk)
    cc = this._child_cache[base_pk]
    b = set()
    children = cc.get(term_pk)
    if (children):
        stack = list(children)
        while (stack):
            tpk = stack.pop()
            children = cc.get(tpk)
            if (children):
                for child in children:
                    stack.append(child)
            b.add(tpk)
    return b
    
# base_pks
def base_term_pks(base_pk):
    '''
    All pks in a base.
    @return set of term pks
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

def _term_element_count(term_pk):
    '''
    Count of elems on a single term
    '''
    assert isinstance(base_pk, int), "Not an integer!"
    assert isinstance(term_pk, int), "Not an integer!"
    r = this._count.get[base_pk]
    if (not r):
        r = Element.objects.filter(term__exact=term_pk).count()
        this._count[term_pk] = r
    return r
    
def term_descendant_element_count(term_pk):
    termpk = int(term_pk)
    count = _term_element_count(termpk)
    for tpk in term_descendant_pks(termpk):
        count = count + term_element_count(tpk)
    return count
