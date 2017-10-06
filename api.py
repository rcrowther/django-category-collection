from .models import Base, Term, BaseTerm, TermParent, Element
from taxonomy import cache
 
## Facade for cache and Model/Model manager methods for consistent 
# (non-web restricted) interface

# constants
ROOT = TermParent.NO_PARENT
FULL_DEPTH = cache.FULL_DEPTH
UNPARENT = TermParent.UNPARENT
# Cache-based

#def base(base_pk):
    #return cache.base(base_pk)
    
#def term(term_pk):
    #return cache.term(term_pk)

#def term_parents(base_pk, term_pk):
    #return cache.term_parents(base_pk, term_pk)

#def term_parent_pks(base_pk, term_pk):
    #return cache.term_parent_pks(base_pk, term_pk)

#def term_children(base_pk, term_pk):
    #return cache.term_children(base_pk, term_pk)

#def term_child_pks(base_pk, term_pk):
    #return cache.term_child_pks(base_pk, term_pk)
    
#def term_ancestor_paths(base_pk, term_pk):
    #return cache.term_ancestor_paths(base_pk, term_pk)
      
#def term_descendant_paths(base_pk, term_pk):
    #return cache.term_descendant_paths(base_pk, term_pk)

#def term_ancestor_pks(base_pk, term_pk):
    #return cache.term_ancestor_pks(base_pk, term_pk)

#def term_descendant_pks(base_pk, term_pk):
    #return cache.term_descendant_pks(base_pk, term_pk)
    
#def base_term_pks(base_pk):
    #return cache.base_term_pks(base_pk)

#def terms_flat_tree(base_pk, parent_pk=ROOT, max_depth=FULL_DEPTH):
    #return cache.terms_flat_tree(base_pk, parent_pk, max_depth)


## Model-based
#def base_create(title, slug, description, is_single, weight):
    #return Base.system.create(title, slug, description, is_single, weight)
    
#def base_update(base_pk, title, slug, description, is_single, weight):
    #cache.base_clear(base_pk)
    #return Base.system.update(base_pk, title, slug, description, is_single, weight)

#def base_delete(base_pk):
    #cache.base_and_tree_clear(base_pk)
    #return Base.system.delete(base_pk)


#def base_terms_ordered(base_pk):
    #return BaseTerm.system.terms_ordered(base_pk)
    
#def base_set_is_single(base_pk, is_single):
    #cache.base_and_tree_clear(base_pk)
    #Base.system.set_is_single(base_pk, is_single)

#def term_create(base_pk, parent_pks, title, slug, description, weight):
    #cache.tree_parentage_clear(base_pk)
    #return Term.system.create(base_pk, parent_pks, title, slug, description, weight)

#def term_update(parent_pks, term_pk, title, slug, description, weight):
    #cache.term_and_tree_clear(term_pk)
    #return Term.system.update(parent_pks, term_pk, title, slug, description, weight)
      
#def term_delete(term_pk):
    #cache.tree_clear(term_pk)
    #return Term.system.delete(term_pk)

#def term_by_title(title):
#    return Term.objects.get(title__exact=title)

#? and a base?
#def term_base_pk(term_pk):
    #return BaseTerm.system.base_pk(term_pk)
    
#def term_title_search(base_pk, pattern):
#    return Term.system.title_search(base_pk, pattern)
    
#def element_add(term_pk, element_pk):
    #cache.element_clear_term(term_pk)
    #return Element.system.add(term_pk, element_pk)
         
#def element_delete(term_pk, element_pk):
    #cache.element_clear_term(term_pk)
    #return Element.system.delete(term_pk, element_pk)

#def element_bulk_merge(term_pks, element_pk):
    #cache.element_clear_all()
    #return Element.system.bulk_merge(term_pks, element_pk)
            
#def element_base_delete(base_pk, element_pks):
    #cache.element_clear_all()
    #return Element.system.delete(base_pk, element_pks)
    
#def element_terms(base_pk, element_pk): 
#    return Element.system.terms(base_pk, element_pk)

#def term_elements(term_pk, model): 
#    pks = Element.objects.filter(term=term_pk)
#    return model.objects.filter(pk__in=pks)


class ElementAPI():
    def __init__(self, element_pk):
        self.pk = int(element_pk)

    def terms(self, base_pk): 
        return Element.system.terms(int(base_pk), self.pk)
     
    def add(self, term_pk):
        cache.element_clear_term(term_pk)
        return Element.system.add(term_pk, self.pk)
             
    def delete(self, term_pk):
        cache.element_clear_term(term_pk)
        return Element.system.delete(term_pk, self.pk)
    
    def merge(self, term_pks):
        #! test for int?
        cache.element_clear_all()
        return Element.system.bulk_merge(term_pks, self.pk)
                
    def base_delete(self, base_pk):
        cache.element_clear_all()
        return Element.system.base_delete(int(base_pk), self.pk)
       
  
class TermAPI():
    def __init__(self, term_pk, base_pk=None):
        self.pk = int(term_pk)
        #! lazy?
        if (base_pk is None):
            base_pk = BaseTerm.system.base_pk(term_pk)
        self._base_pk = int(base_pk)


    def update(self, parent_pks, title, slug, description, weight):
        cache.term_and_tree_clear(self.pk)
        return Term.system.update(parent_pks, self.pk, title, slug, description, weight)
          
    def delete(self):
        cache.tree_clear(self.pk)
        return Term.system.delete(self.pk)
        
    def term(self):
        return cache._term_cache.get(self.pk)
    
    def base_pk(self):
        return self._base_pk 
        
    def base(self):
        return base(self._base_pk)
            
    def parents(self):
        return cache.term_parents(self._base_pk, self.pk)
    
    def parent_pks(self):
        return cache.term_parent_pks(self._base_pk, self.pk)
    #! dont throw errors on leaves
    def children(self):
        return cache.term_children(self._base_pk, self.pk)
    #! don't throw errors on leaves
    def child_pks(self):
        return cache.term_child_pks(self._base_pk, self.pk)
        
    def ancestor_paths(self):
        return cache.term_ancestor_paths(self._base_pk, self.pk)
          
    def descendant_paths(self):
        return cache.term_descendant_paths(self._base_pk, self.pk)
    
    def ancestor_pks(self):
        return cache.term_ancestor_pks(self._base_pk, self.pk)
    
    def descendant_pks(self):
        return cache.term_descendant_pks(self._base_pk, self.pk)
        
    def elements(self, model): 
        pks = Element.objects.filter(term=self.pk)
        return model.objects.filter(pk__in=pks)

    
class BaseAPI():
    def __init__(self, base_pk):
        self.pk = int(base_pk)
        
    def term_create(self, parent_pks, title, slug, description, weight):
        cache.tree_parentage_clear(self.pk)
        return Term.system.create(self.pk, parent_pks, title, slug, description, weight)    

    def update(self, title, slug, description, is_single, weight):
        cache.base_clear(self.pk)
        return Base.system.update(self.pk, title, slug, description, is_single, weight)
    
    def delete(self):
        cache.base_and_tree_clear(self.pk)
        return Base.system.delete(self.pk)
  

    def base(self):
        ''' model of base data '''
        return cache._base_cache.get(self.pk)
        
    def term_pks(self):
        ''' set of all (non-duplicated) term pks'''
        return cache.base_term_pks(self.pk)

    def terms_ordered(self):
        ''' list of tuples of all term data, ordered'''
        return BaseTerm.system.terms_ordered(self.pk)

    def _get_is_single(self):
         return self.base().is_single

    def _set_is_single(self, is_single):
        cache.base_and_tree_clear(self.pk)
        Base.system.set_is_single(self.pk, is_single)
        
    is_single = property(_get_is_single, _set_is_single)

    def children(self):
        return cache.term_children(self.pk, ROOT)
        
    def flat_tree(self, parent_pk=ROOT, max_depth=FULL_DEPTH):
        return cache.flat_tree(self.pk, parent_pk, max_depth)

    def flat_tree_pks(self, parent_pk=ROOT, max_depth=FULL_DEPTH):
        return cache.flat_tree_pks(self.pk, parent_pk, max_depth)
        
    def stacked_tree(self, parent_pk=TermParent.NO_PARENT, max_depth=FULL_DEPTH):
        return cache.stacked_tree_iter(self.pk, parent_pk, max_depth)
        
    def element_terms(self, element_pk): 
        return Element.system.terms(self.pk, int(element_pk))



def _base_ordered():
    return Base.system.ordered()

def _base_create(title, slug, description, is_single, weight):
    return Base.system.create(title, slug, description, is_single, weight)

def _cache_clear():
    return cache.clear()
    
def Taxonomy(title):
    '''
    Factory for BaseAPI.
    Usage:
    Taxonomy(title)
    Taxonomy.pk(base_pk)
    Taxonomy.slug(slug)
    Taxonomy.term(term_pk)
    Taxonomy.base(base_pk)
    also:
    Taxonomy.base_ordered() returns a QuerySet of bases
    Taxonomy.base_create() 
    Taxonomy.cache_clear() 
    @throws Base.DoesNotExist
    @return an BaseAPI object
    '''
    # taxonomy.models.DoesNotExist:
    return BaseAPI(Base.objects.get(title=title).pk)
    
Taxonomy.pk = lambda base_pk : BaseAPI(base_pk)
Taxonomy.slug = lambda slug : BaseAPI(Base.objects.get(slug=slug).pk)
Taxonomy.term = lambda term_pk : cache._term_cache.get(term_pk)
Taxonomy.base = lambda base_pk : cache._base_cache.get(base_pk)
Taxonomy.ordered = _base_ordered
Taxonomy.base_create = _base_create
Taxonomy.cache_clear = _cache_clear

