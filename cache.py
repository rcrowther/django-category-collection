
from .models import Term, Base, TermParent, BaseTerm, Element
import sys
from collections import namedtuple
from functools import partial

#! are pk versions necessary?
#! derive base from term or insist on supply?

# Pointer to the module object instance, for module-wide storage.
# https://stackoverflow.com/questions/1977362/how-to-create-module-wide-variables-in-python#1978076
this = sys.modules[__name__]


class AllQueryCache():
    '''
    This tiny class has a trick, it bulkloads on startup and clear_all().
    Neater and (depends on the efficiency of the supplied callback)
    maybe a lot faster. 
    @param bulk_load_callback a value
    @param single_load_callback [(k,v)...]. Key is converted to int
    '''
    def __init__(self, bulk_load_callback, single_load_callback):
        self.cache = {}
        self.bulk_load_callback = bulk_load_callback
        self.single_load_callback = single_load_callback
        self.bulk_load()
    
    def get(self, pk):
        assert isinstance(pk, int), "Not an integer!"
        r = self.cache.get(pk)
        if (r is None):
          r = self.single_load_callback(pk)
          self.cache[pk] = r
        return r
        
    def bulk_load(self):
        qs = self.bulk_load_callback()
        for e in qs:
            self.cache[int(e[0])] = e[1]
           
    def clear_one(self, pk):
        assert isinstance(pk, int), "Not an integer!"
        try:
            del(self.cache[pk])
        except KeyError:
          pass
                 
    def clear_some(self, pks):
      for pk in pks:
          self.clear_one(int(pk))
          
    def clear_all(self):
        self.cache = {}
        self.bulk_load()
    
    def contains(self, pk):
        return (pk in self.cache)
            
    def __str__(self):
        return str(self.cache)
        


def _one_base(pk):
    return Base.objects.get(pk__exact=pk)

def _all_bases():
    r = Base.objects.all()
    b = []
    for e in r:
        b.append((e.pk, e))
    return b 

# cache of base data    
this._base_cache = AllQueryCache(
    _all_bases,
    _one_base
    )


# cache of hierarchial associations
# {tree_id: {term_id: [associated_term_ids]}}
this._child_cache = {}
this._parent_cache = {}


# storage tuple
TermFTData = namedtuple('TermFTData', ['pk', 'title', 'slug', 'description', 'depth'])



def _one_term(pk):
    return Term.objects.get(pk__exact=pk)

def _all_terms():
    r = Term.objects.all()
    b = []
    for t in r:
        b.append((t.pk, t))
    return b 

this._term_cache = AllQueryCache(
    _all_terms,
    _one_term
    )


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
    b.append('base cache:')
    b.append(str(this._base_cache))
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
        # value must come from the database, not cache :)
        # made runtime check, not assert, as all kinds of user
        # interaction can make it's way here
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
          #this._term_cache[base_pk] = {}
          #tc = this._term_cache[base_pk]
          #for t in BaseTerm.system.term_iter(base_pk):
          #    tc[t.pk] = t

import time
def timing(f):
    def wrap(*args):
        time1 = time.time()
        ret = f(*args)
        time2 = time.time()
        print('function took %0.3f ms' % ( (time2-time1)*1000.0))
        return ret
    return wrap
        

FULL_DEPTH = None
#! mutability will hurt, even here
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
    
    if (not (this._term_cache.contains(parentpk) or (parentpk == TermParent.NO_PARENT))):
        raise KeyError('Flat tree can not be returned because given parent key not in the base: parent key:{0}'.format(parentpk))
        
    # jump access to these caches
    children = this._child_cache[basepk]
    parents = this._parent_cache[basepk]
    term_data = this._term_cache
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
                # exhausted. Pop a iter at a previous depth
                break
            td = term_data.get(pk)
            td.depth = depth
            #tree.append(TermFTData(pk, td.title, td.slug, td.description, depth))
            tree.append(td)
            child_pks = children.get(pk)
            if (child_pks and (depth < _max_depth)):
                # append current iter, will return after processing children
                stack.append(it)
                # append new depth of iter
                stack.append(iter(child_pks))
                #break
    return tree
    
    
#STGroupData = namedtuple('STGroupData', ['parent_idx', 'group'])
class STGroupData:
    def __init__(self, parent_idx, group):
        self.parent_idx = parent_idx
        self.data = group
    def __str__():
        return 'STG-' + str(self.parent_idx)
        
def stacked_tree(base_pk, parent_pk=TermParent.NO_PARENT, max_depth=FULL_DEPTH):
    basepk = int(base_pk)
    parentpk = int(parent_pk)
    tree = []

    _assert_cache(basepk)
    
    if (not (this._term_cache.contains(parentpk) or (parentpk == TermParent.NO_PARENT))):
        raise KeyError('Flat tree can not be returned because given parent key not in the base: parent key:{0}'.format(parentpk))
        
    # jump access to these caches
    children = this._child_cache[basepk]
    parents = this._parent_cache[basepk]
    term_data = this._term_cache
    _max_depth = (len(children) + 1) if (max_depth is None) else max_depth
    if ((_max_depth < 1) or (parentpk not in children)):
        # if depth == 0 this is an empty list. Also...
        # if exists but has no children, must be a leaf
        return []
        
    # Stack of levels to process. Each level is an iter.
    # preload with the first set of children
    depth = 1
    layer = [list(children[parentpk])]
    next_layer = []
    layers = []
    data_layer = [STGroupData(0, list(children[parentpk]))]
    while (layer and depth <= _max_depth):
            layers.append(data_layer)
            next_layer = []
            data_layer = []
            idx = 0
            for group in layer:
                for pk in group:
                    xc = children.get(pk)
                    if (xc):
                        data_layer.append(STGroupData(idx, list(xc)))
                        next_layer.append(list(xc))
                    idx = idx + 1
            layer = next_layer
            depth = depth + 1

    return layers


    
def title(pk):
    return this._term_cache.get(pk).title
import math

def angle(b, x_from, x_to, y_from):
    y_to = y_from - 24 
    b.append('<polyline points="{0},{2} {0},{3} {1},{3}" style="fill:none;stroke:black;stroke-width:3" />'.format(x_from, x_to, y_from, y_to))

def stub(b, x_from, y_from):
    y_to = y_from - 24 
    b.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" style="stroke:rgb(255,0,0);stroke-width:2" />'.format(x_from, y_from, y_to))

def beam(b, x_from, x_to, y):
    y = y - 24 
    b.append('<line x1="{0}" y1="{2}" x2="{1}" y2="{2}" style="stroke:rgb(255,0,0);stroke-width:2" />'.format(x_from, x_to, y))

class RendBeam:
    def __init__(self, b, y, height, x_offset=0, color='black'):
        self.b = b
        self.y = y
        self.x_offset = x_offset
        self.y_beam = y - height
        self.height = height
        self.first_stem_x = None
        self.last_stem_x = None
        self.first = True
        self.color = color
        
    def stem(self, x):
        x = x + self.x_offset
        y_to = self.y_beam            
        if (self.first):
            self.first = False
            self.first_stem_x = x
            y_to = y_to - self.height
        self.last_stem_x = x
        self.b.append('<line x1="{0}" y1="{1}" x2="{0}" y2="{2}" style="stroke:{3};stroke-width:2" />'.format(x, self.y, y_to, self.color))

    def beam(self):
        self.b.append('<line x1="{0}" y1="{2}" x2="{1}" y2="{2}" style="stroke:{3};stroke-width:2" />'.format(self.first_stem_x, self.last_stem_x, self.y_beam, self.color))
      
def rend_tree(tree, x_space, y_space, data_callback):
    # The dummy div is filled later when the height can be calculated 
    b = ['dummy_div']
    tree_len = len(tree)
    x_half = math.floor(x_space / 2)
    y_head = y_space #math.floor(y_space / 2)
    depth = 0
    x = 0
    y = 0
    prev_idx_pos = [0 for x in range(20)]
    term_data = this._term_cache
    for layer in tree:
        y = y_head + ((depth) * y_space)
        x = 0
        idx = 0
        for group in layer:
            data = group.data
            parent_idx = group.parent_idx
            x = prev_idx_pos[parent_idx]
            x_start = x
            rb = RendBeam(b, y - 16, 12, 12, 'rgb(0,220,126)')
            for pk in data:
                prev_idx_pos[idx] = x
                rb.stem(x)
                b.append('<text x="{0}" y="{1}">{2}</text>'.format(x, y, term_data.get(pk).title))
                x = x + x_space
                idx = idx + 1
            x_end = x - x_space + 1
            rb.beam()    
        depth = depth + 1
    b.append('</svg>')
    #b[0] = '<svg width="{0}" height="{1}">'.format(600, max_depth * y_space)
    b[0] = '<svg width="{0}" height="{1}">'.format(600, depth * y_space)
    return ''.join(b)

#def rend_flat_tree(tree, x_space, y_space, data_callback):
    ## The dummy div is filled later when the height can be calculated 
    #b = ['dummy_div']
    #tree_len = len(tree)
    #x_half = math.floor(x_space / 2)
    #y_head = math.floor(y_space / 2)
    #x_at_depth = [0 for i in range(len(tree))]
    #prev_pos_at_depth = [0 for i in range(len(tree))]
    #last_depth = 0
    #max_depth = 0
    #x = 0
    #y = 0
    #for e in tree:
        #depth = e.depth
        #max_depth = max(max_depth, depth)
        
        #if (depth < last_depth):
            #stub(b, x + x_half, y)
            #for d in range(last_depth):
              #prev_pos_at_depth[d]
        #elif (depth > last_depth):
            ##angle(b, x + x_half, x + x_half + x_space, y)
            #pass
        #else:
           #angle(b, x + x_half, x + x_half + x_space, y)

        #y = y_head + ((depth - 1) * y_space)

        #if (depth <= last_depth):
            #x_at_depth[depth] = x_at_depth[depth] + x_space
        #else:
            #x_at_depth[depth] = x_at_depth[last_depth]
        #x = x_at_depth[depth]


        ##b.append('<span style="position:absolute; left:{0}px;top:{1}px">{2}</span>'.format(x, y, e.title))
        #b.append('<text x="{0}" y="{1}">{2}</text>'.format(x, y, e.title))
        #prev_pos_at_depth[depth] = (x, y)
        #last_depth = depth
    ##b.append('</div>')
    #b.append('</svg>')
    ##b[0] = '<div class="tree" style="position:relative; height:{0}px">'.format(max_depth * y_space)
    #b[0] = '<svg width="{0}" height="{1}">'.format(600, max_depth * y_space)
    #return ''.join(b)

def rend_flat_tree_right(tree, x_space, y_space, data_callback):
    # The dummy div is filled later when the height can be calculated 
    b = ['dummy_div']
    tree_len = len(tree)
    x_at_depth = [0 for i in range(len(tree))]
    last_depth = 0
    max_depth = 0
    for e in reversed(tree):
        depth = e.depth
        max_depth = max(max_depth, depth)
        y = (depth - 1) * y_space
        if (depth <= last_depth):
            x_at_depth[depth] = x_at_depth[depth] - x_space
        else:
            x_at_depth[depth] = x_at_depth[last_depth]
        x = x_at_depth[depth]
        b.append('<span style="position:absolute; left:{0}px;top:{1}px">{2}</span>'.format(x, y, e.title))
        last_depth = depth
    b.append('</div>')
    b[0] = '<div class="tree" style="position:relative; height:{0}px">'.format(max_depth * y_space)
    return ''.join(b)
                  
def base_clear(base_pk):
    '''
    Clear cached data on base update. 
    For update on a Base. There is no need to touch other
    data.
    '''
    this._base_cache.clear_one(base_pk)

def tree_parentage_clear(base_pk):
    '''
    Clear the tree.
    Used on term creation.
    '''
    assert isinstance(base_pk, int), "Not an integer!"
    try:
        del(this._child_cache[base_pk])
    except KeyError:
      pass

def term_and_tree_clear(term_pk):
    '''
    Clear a term and the tree.
    Used for term update. 
    '''
    assert isinstance(term_pk, int), "Not an integer!"
    base_pk = BaseTerm.system.base_pk(term_pk)
    tree_parentage_clear(base_pk)
    this._term_cache.clear_one(term_pk)
    this._count.clear_one(term_pk)
        
def base_and_tree_clear(base_pk):
    '''
    Clears a tree and the base. 
    Used on base delete and setting single parent.
    '''
    base_clear(base_pk)
    tree_parentage_clear(base_pk)
    # demolition, unless we recover deleted terms?
    this._term_cache.clear_all()
    this._count.clear_all()

def tree_clear(term_pk):
    '''
    Clear cached data for a tree
    Used on on term delete. Term delete causes recursive deletion, so 
    all base info needs invalidating.
    '''
    assert isinstance(term_pk, int), "Not an integer!"
    base_pk = BaseTerm.system.base_pk(term_pk)
    tree_parentage_clear(base_pk)
    this._term_cache.clear_all()
    this._count.clear_all()

def element_clear_term(term_pk):
    this._count.clear_one(term_pk)

#+       
#def element_clear_tree(tree_pk):
    # demolition, as it can remove from anyplace
    #this._count = {}

def element_clear_all():
    this._count.clear_all()
    
def clear():
    '''
    Reset all caches.
    *hint* drastic measures ...or general purpose.
    '''
    this._base_cache = {}
    #this._term_cache = {}
    this._child_cache = {}
    this._parent_cache = {}
    #this._count = {}
    this._term_cache.clear_all()
    this._count.clear_all()

def base(base_pk):
    '''
    Term from a pk.
    From cache.
    
    @param base_pk int or int-coercable string 
    @param term_pk int or int-coercable string 
    @return a term.
    '''
    return this._base_cache.get(base_pk)
    
#def term(base_pk, term_pk):
def term(term_pk):
    '''
    Term from a pk.
    From cache.
    
    @param base_pk int or int-coercable string 
    @param term_pk int or int-coercable string 
    @return a term.
    '''
    return this._term_cache.get(term_pk)

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
    return [this._term_cache.get(pk) for pk in pks]
  
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
    return [this._term_cache.get(pk)  for pk in pks]

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
    term_data = this._term_cache
    
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
                  dt = [term_data.get(pk) for pk in trail]
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
    termc = this._term_cache
    
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
                  dt = [termc.get(pk) for pk in trail]
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


def _one_elem(pk):
    return int(Element.objects.filter(term__exact=pk).count)

def _all_elems():
    r = Term.objects.values_list('pk', flat=True)
    b = []
    for tpk in r:
        count = Element.objects.filter(term__exact=tpk).count()
        b.append((tpk, int(count)))
    return b 

this._count = AllQueryCache(
    _all_elems,
    _one_elem
    )

def term_descendant_element_count(base_pk, term_pk):
    termpk = int(term_pk)
    count = this._count.get(termpk)
    for tpk in term_descendant_pks(base_pk, termpk):
        count = count + this._count.get(tpk)
    return count
