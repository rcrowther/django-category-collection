from taxonomy import cache
#from .cache import (
#FULL_DEPTH,
#base, term, term_parents, term_children, 
#term_ancestor_paths, term_descendant_paths,
#base_term_pks, terms_flat_tree
#)

from .models import Base, Term, BaseTerm, TermParent, Element
 
## Facade for cache and Model/Model manager methods for consistent 
# (non-web restricted) interface

# Cache-based

def base(base_pk):
    return cache.base(base_pk)
    
def term(base_pk, term_pk):
    return cache.term(base_pk, term_pk)

def term_parents(base_pk, term_pk):
    return cache.term_parents(base_pk, term_pk)

def term_parent_pks(base_pk, term_pk):
    return cache.term_parent_pks(base_pk, term_pk)

def term_children(base_pk, term_pk):
    return cache.term_children(base_pk, term_pk)

def term_child_pks(base_pk, term_pk):
    return cache.term_child_pks(base_pk, term_pk)
    
def term_ancestor_paths(base_pk, term_pk):
    return cache.term_ancestor_paths(base_pk, term_pk)
      
def term_descendant_paths(base_pk, term_pk):
    return cache.term_descendant_paths(base_pk, term_pk)

def term_ancestor_pks(base_pk, term_pk):
    return cache.term_ancestor_pks(base_pk, term_pk)

def term_descendant_pks(base_pk, term_pk):
    return cache.term_descendant_pks(base_pk, term_pk)
    
def base_term_pks(base_pk):
    return cache.base_term_pks(base_pk)

def terms_flat_tree(base_pk, parent_pk=TermParent.NO_PARENT, max_depth=cache.FULL_DEPTH):
    return cache.terms_flat_tree(base_pk, parent_pk, max_depth)
    



def cache_clear():
    return cache.clear()

## Model-based
def base_create(title, slug, description, is_single, weight):
    cache.base_merge_clear()
    return Base.system.create(title, slug, description, is_single, weight)
    
def base_update(base_pk, title, slug, description, is_single, weight):
    cache.base_merge_clear()
    return Base.system.update(base_pk, title, slug, description, is_single, weight)

def base_delete(base_pk):
    cache.base_delete_clear(base_pk)
    return Base.system.delete(base_pk)

def base_ordered():
    return Base.system.ordered()

def base_is_single(base_pk, is_single):
    return Base.system.is_single(base_pk, is_single)

def term_create(base_pk, parent_pks, title, slug, description, weight):
    cache.term_merge_clear(base_pk)
    return Term.system.create(base_pk, parent_pks, title, slug, description, weight)

def term_update(parent_pks, term_pk, title, slug, description, weight):
    cache.term_merge_clear(term_base_pk(term_pk))
    return Term.system.update(parent_pks, term_pk, title, slug, description, weight)
      
def term_delete(term_pk):
    cache.term_delete_clear(term_pk)
    return Term.system.delete(term_pk)

#? or a base?
def term_base_pk(term_pk):
    return BaseTerm.system.base_pk(term_pk)
    
def element_merge(term_pks, element_pk):
    cache.element_merge_clear(term_pks)
    return Element.system.merge(term_pks, element_pk)
            
def element_delete(base_pk, element_pks):
    cache.element_remove_clear()
    return Element.system.delete(base_pk, element_pks)
    
def element_terms(base_pk, element_pk): 
    return Element.system.terms(base_pk, element_pk)

# how about elements in terms?
# this ok?
def term_elements( term_pk, model): 
    pks = Element.objects.filter(term_pk)
    return model.objects.filter(pk__in=pks)
