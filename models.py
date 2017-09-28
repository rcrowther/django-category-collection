from django.db import models
from django.core.urlresolvers import reverse
from django.db import connection

# Create your models here.


class BaseManager(models.Manager):
    def create(self, title, slug, description, is_single, weight):
        '''
        Create a base.
        @param parents an array of pk
        @return the created base model.
        '''
        o = Base(
            title=title,
            slug=slug,
            description=description,
            is_single=is_single,
            is_unique=True,
            weight=weight
            )
        o.save()
        return o  
          
    def update(self, base_pk, title, slug, description, is_single, weight):
        '''
        Update a base.
        @param parents an array of pk
        '''
        o = Base( 
          pk=base_pk,
          title=title,
          slug=slug,
          description=description,
          is_single=is_single,
          is_unique=True,
          weight=weight
          )
        o.save()
        return o
  
    def delete(self, base_pk):
        '''
        Delete a base.
        @param parents an array of pk
        '''
        # term data
        all_term_pks = list(BaseTerm.objects.filter(base__exact=base_pk).values_list('term', flat=True))
        # elems
        Element.objects.filter(term__in=all_term_pks).delete()
        # hierarchy
        TermParent.objects.filter(term__in=all_term_pks).delete()
        # term bases
        BaseTerm.objects.filter(term__in=all_term_pks).delete()
        # terms
        Term.objects.filter(pk__in=all_term_pks).delete()
        # tree
        Base.objects.get(pk__exact=base_pk).delete() 
           
    def ordered(self):
        '''
        All base objects, ordered.
        Ordered by weight and title, in that order.
        @return [base...]
        '''  
        return Base.objects.order_by('weight', 'title').all()

        
    _SQLIsSingle = "UPDATE taxonomy_base SET is_single=%s  WHERE id = %s"
    def is_single(self, base_pk, is_single):
        '''
        Set parent status field.
        Silent operation.
        '''
        #! restore, when SQL is correct
        c = connection.cursor()
        try:
            c.execute(self._SQLIsSingle, [is_single, base_pk])
        finally:
            c.close()
  

        
#? names and slugs do not have to be unique, as we may want to 
# structure a website, for example, and there may be several 'news'
# terms under 'sports', 'local', 'culture' etc.
# On the other hand, that means slugs can not be used for URLs. 
# It seems ok to enforce uniqueness within a term, but this is not the
# place for that.
#? That means a unique identifier from the data could be parent-term? 
  
#? 'We do want an id field here'. Maybe we do, it makes duplicate removal easy?
class Base(models.Model):
    '''
    parent can be null, for top level. Therefore can be root also.
    '''
    title = models.CharField(
      max_length=255,
      db_index=True,
      help_text="Name for a tree of categories. Limited to 255 characters.",
      )
  
    slug = models.SlugField(
      max_length=64,
      unique=True,
      help_text="Short name for use in urls.",
      )
      
    description = models.CharField(
      max_length=255,
      blank=True,
      default='',
      help_text="Overall description of the collection of categories. Limited to 255 characters.",
      )
      
    is_single = models.BooleanField(
      default=True,
      help_text="Nunber of parents allowed for a term in the taxonomy (True = one only, False = many).",
      )
      
    is_unique = models.BooleanField(
      default=False,
      help_text="Nunber of parents allowed for a element in the taxonomy (True = one only, False = many).",
      )
      
    weight = models.PositiveSmallIntegerField(
      blank=True,
      default=0,
      db_index=True,
      help_text="Priority for display in some templates. Lower value orders first. 0 to 32767.",
      )
  
    objects = models.Manager()
    system = BaseManager()
    
    def get_absolute_url(self):
        return reverse("base-detail", kwargs={"slug": self.slug})
  
    def __str__(self):
      return "{0}".format(
      self.title, 
      )
    


class TermManager(models.Manager):
    def create(self, base_pk, parent_pks, title, slug, description, weight):
      '''
      Create a term.
      @param parent_pks an array of pk
      @return the created term model.
      '''
      o = Term( 
        title=title,
        slug=slug,
        description=description,
        weight=weight
        )
      o.save()
      BaseTerm.system.create(base_pk, o.pk)
      TermParent.system.merge(o.pk, parent_pks)
      return o
  
  
    def update(self, parent_pks, term_pk, title, slug, description, weight):
      o = Term(
        pk=term_pk,
        title=title,
        slug=slug,
        description=description,
        weight=weight
        )
      o.save()
      TermParent.system.merge(term_pk, parent_pks)
      return o
  
    def _delete_one(self, term_pk):
        # elems
        Element.objects.filter(term__exact=term_pk).delete()
        # hierarchy
        TermParent.objects.filter(term__exact=term_pk).delete()
        # term bases
        BaseTerm.objects.filter(term__exact=term_pk).delete()
        # term
        Term.objects.filter(pk__exact=term_pk).delete()

          
    #? Not taking advantage of the caches here?
    # do I care?
    def delete(self, term_pk):
      stash=[term_pk]
      while stash:
        tpk = stash.pop()
        children = TermParent.objects.filter(parent__exact=tpk).values_list('term', flat=True)
        
        for child_pk in children:
          parent_count = TermParent.objects.filter(term__exact=child_pk).count()
          # i.e the child has only one parent, this term, so stash
          # for removal
          if ( parent_count < 2 ):
            stash.append(child_pk)
                  
        self._delete_one(tpk)
  

    _SQLTreePK = "SELECT id FROM taxonomy_term t, taxonomy_baseterm bt WHERE t.id = bt.term and bt.base = %s ORDER BY t.weight, t.title"
    def term_pks_ordered(self, base_pk):
        '''
        Term pks for a given base.
        The term pks are ordered by weight and title, in that order.
        @return [term_pk...]
        '''      
        c = connection.cursor()
        try:
            c.execute(self._SQLTreePK, [base_pk])
            r = [e for e in c.fetchall()]
        finally:
            c.close()
        return r


          
    #- usused, should not be here?
    _SQLParents = "SELECT t.id, t.title, t.slug, t.description FROM taxonomy_term t, taxonomy_termparent h WHERE t.id = h.parent and h.term = %s ORDER BY t.weight, t.title"
    def parents_ordered(self, term_pk):
        '''
        Parent term data for a given tree.
        The term pks are ordered by weight and title, in that order.
        NB: raw SQL query
        
        @return [term...]
        '''
        c = connection.cursor()
        try:
            c.execute(self._SQLParents, [term_pk])
            r = [e for e in c.fetchall()]
        finally:
            c.close()
        return r
        
    #- usused, should not be here?
    _SQLChildren = "SELECT t.id, t.title, t.slug, t.description FROM taxonomy_term t, taxonomy_termparent h WHERE  t.id = h.term and h.parent = %s ORDER BY t.weight, t.title"
    def children_ordered(self, pk):
        '''
        child term data for a given tree.
        The term pks are ordered by weight and title, in that order.
        NB: raw SQL query
        
        @return [term...]
        '''
        c = connection.cursor()
        try:
            c.execute(self._SQLChildren, [pk])
            r = [e for e in c.fetchall()]
        finally:
            c.close()
        return r
  
  # This, or just is_single?
    #_SQLBase = "SELECT tr.* FROM taxonomy_tree tr, taxonomy_term t WHERE tr.id = t.tree and t.id = %s"
    #def tree(self, termpk):
        #'''
        #Base for given term
        #'''
        #c = connection.cursor()
        #r = None
        #try:
            #c.execute(self._SQLBase, [termpk])
            #r = c.fetchone()
        #finally:
            #c.close()
        #return r
        
        

class Term(models.Model):
      
    # Not unique. All terms in same table, different taxonomies.
    title = models.CharField(
      max_length=255,
      db_index=True,
      help_text="Name for the category. Limited to 255 characters.",
      )
      
    # Not unique. Terms may be in different taxonomies. They may
    # be duplicated at different places in a hierarchy e.g. 'sports>news'
    # 'local>news'.
    slug = models.SlugField(
      max_length=64,
      # unique specifies index
      #db_index=True,
      #unique=True,
      help_text="Short name for use in urls.",
      )
  
    description = models.CharField(
      max_length=255,
      blank=True,
      default='',
      help_text="Description of the category. Limited to 255 characters.",
      )
      
    weight = models.PositiveSmallIntegerField(
      blank=True,
      default=0,
      db_index=True,
      help_text="Priority for display in some templates. Lower value orders first. 0 to 32767.",
      )
  
    objects = models.Manager()
    system = TermManager()
       
    def get_absolute_url(self):
      return reverse("term-detail", kwargs={"slug": self.slug})
  
    def __str__(self):
      return "{0}".format(
      self.title, 
      )


class BaseTermManager(models.Manager):
    def create(self, base_pk, term_pk):
      o = BaseTerm(base_pk, term_pk)
      o.save()

    def delete(self, term_pk):
      BaseTerm.objects.filter(term__exact=term_pk).delete()

    def term_pks(self, base_pk):
      return BaseTerm.objects.filter(base__exact=base_pk).values_list('term', flat=True)
    
    def base_pk(self, term_pk):
      o = BaseTerm.objects.get(term__exact=term_pk)
      return o.base
    
    _SQLTreeTerm = "SELECT * FROM taxonomy_term, taxonomy_baseterm bt WHERE bt.base = %s and id = bt.term"
    def term_iter(self, base_pk):
      '''
      Parent/term pks for a given tree.
      The term pks are ordered by weight and title, in that order.
      
      @param func (term_id, parent_id) as raw fetchall.
      '''      
      # Django usually does this for us but, without Foreign Keys
      # the join must be manually constructed.
      with connection.cursor() as c:
          c.execute(self._SQLTreeTerm, [base_pk])
          for e in c.fetchall():
              yield Term(pk=e[0], title=e[1], slug=e[2], description=e[3], weight=e[4])      
      
    #! ordered_terms
    _SQLTree = "SELECT t.id, t.title, t.slug, t.description FROM taxonomy_term t, taxonomy_baseterm bt WHERE bt.base = %s and id = bt.term  ORDER BY t.weight, t.title"
    def ordered(self, base_pk):
        '''
        terms for a given base.
        The term pks are ordered by weight and title, in that order.
        @return [(term)...]
        '''  
        c = connection.cursor()
        try:
            c.execute(self._SQLTree, [base_pk])
            r = [e for e in c.fetchall()]
        finally:
            c.close()
        return r    


        
    #def search(self, base_pk):
      
class BaseTerm(models.Model):      
    base = models.IntegerField(
      db_index=True,
      help_text="Base associated with a Term.",
      )
      
    term = models.IntegerField(
      primary_key=True, 
      db_index=True,
      help_text="Term associated with a Base",
      )
  
    objects = models.Manager()
    system = BaseTermManager()
    
    def __str__(self):
      return "base({0})-{1}".format(
      self.base, 
      self.term, 
      )
    
    
class TermParentManager(models.Manager):
    def merge(self, term_pk, parent_pks):
        '''
        Create/update parents of a term.
        @param parentpks list of parentpks
        '''
        TermParent.objects.filter(term__exact=term_pk).delete()
        if (isinstance(parent_pks, list)):
            TermParent.objects.bulk_create([TermParent(term=term_pk, parent=p) for p in parent_pks])
        else:
            TermParent(term=term_pk, parent=parent_pks).save()
            
    _SQLTermParentage = "SELECT h.term, h.parent FROM taxonomy_termparent h, taxonomy_term t, taxonomy_baseterm bt WHERE bt.base = %s and bt.term = h.term and t.id = h.term ORDER BY t.weight, t.title"
    #? not sure if this functional approach is best for Python,
    # but code is where it should be (could return a list...)
    def foreach_ordered(self, base_pk, func):
      '''
      Parent/term pks for a given tree.
      The term pks are ordered by weight and title, in that order.
      
      @param func (term_id, parent_id) as raw fetchall.
      '''      
      # order by term
      with connection.cursor() as c:
          c.execute(self._SQLTermParentage, [base_pk])
          for e in c.fetchall():
            func(e)

    _SQLParentage = "SELECT h.term, h.parent FROM taxonomy_termparent h, taxonomy_term t, taxonomy_baseterm bt WHERE bt.base = %s and bt.term = h.term and t.id = h.term ORDER BY t.weight, t.title"
    def iter_ordered(self, base_pk):
      '''
      Term/parent pk pairs for a given tree.
      The term pks are ordered by weight and title, in that order.
      
      @param func (term_id, parent_id) as raw fetchall.
      '''      
      # order by term
      with connection.cursor() as c:
          c.execute(self._SQLParentage, [base_pk])
          for e in c.fetchall():
            yield(e)

    #! probably not fast, but unimportant?
        #? *
    _SQLByBase = "SELECT h.term, h.parent FROM taxonomy_termparent h, taxonomy_term t WHERE t.tree = %s and t.id = h.term"
    def multiple_to_single(self, base_pk):
          '''
          Turn a multiparent tree into a single parent tree.
          This is done by removing duplicate parents. Only the first
          parent is retained.
          Though still fully parented, the tree may display an odd shape
          after this operation.
          
          @return count of parent associations removed
          '''
          # if 'term' is repeated, it must have multiple parents, so:
          # get every parent relation in a tree
          c = connection.cursor()
          qs = None
          try:
              c.execute(self._SQLByBase, [base_pk])
              qs = list(c.fetchall())
          finally:
              c.close()
              
          # build pk list of entries with duplicated term
          seen = []
          duplicate_pks = []
          for e in qs:
              if e[1] in seen:
                  duplicate_pks.append(e[0])
              else:
                  seen.append(e[1])
                  
          # remove pks containing duplicate term fields
          TermParent.objects.filter(pk__in=duplicate_pks).delete()
          return len(duplicate_pks)



# Separate the hierarchy associations
# In a multi taxonomy, Terms may link to several parents.
# Sadly, this means means niether column is unique. Thus, neither can be 
# declaared primary. Thus, an extra default auto-inc column will be
# added.
#? I've grown unhappy with Django's term recovery here, lazy or not. The
# deletion cannot cascade down the related links, and full term recovery
# is excessive, it is often IDs we want. So these fields are not 
#! unwanted id field here
class TermParent(models.Model):
    # Sadly, the autoincrement is dependent on underlying DB 
    # implementation. It would be nice to guarentee zero, but the only
    # way to do this is by an even more awkward method of migration.
    # So -1 sentinel it is, for unparented Terms.
    #- signal to unparent, or as unparented.
    # handy here and there
    UNPARENT = -2
    # Now that would beggar belief, an auto-increment that allows -1...
    NO_PARENT = -1
    
    term = models.IntegerField(
      db_index=True,
      help_text="Term parented by another term.",
      )
      
    # can be self.NO_PARENT, if at root of tree
    parent = models.IntegerField(
      db_index=True,
      help_text="Term parenting another term.",
      )
  

    objects = models.Manager()
    system = TermParentManager()
    
    def __str__(self):
      return "term({0})-{1}".format(
      self.term, 
      self.parent, 
      )
      
      
    
class ElementManager(models.Manager):
    #_SQLCreate = "INSERT INTO taxonomy_termnode VALUES (null, %s, %s, %s)"
    #_SQLDeleteElement = "DELETE FROM taxonomy_termnode WHERE term_id = %s and elem = %s"
    def merge(self, term_pks, element_pk):
        '''
        Create/update an element attachment to terms.
        '''
        #? tad risky, testing only the first?
        base_pk = BaseTerm.system.base(term_pks[0])
        self.delete(base_pk, [element_pk])
        
        elements = []
        if (isinstance(term_pks, list)):
            for tpk in term_pks:
                elements.append(Element(term=tpk, elem=element_pk))      
        else:
            elements.append(Element(tpk, element_pk))     
        Element.objects.bulk_create(elements)

  
  
    def delete(self, base_pk, element_pks):
        '''
        Remove elements from a base. 
        '''
        term_pks = BaseTerm.system.term_pks(base_pk)
        if(isinstance(element_pks, list)):
            Element.objects.filter(term__in=term_pks, elem__in=element_pks).delete()
        else:
            Element.objects.filter(term__in=term_pks, elem__exact=element_pks).delete()
  
    #? any need to order here?
    #? *
    _SQLElementTerms = "SELECT t.id, t.title, t.slug, t.description FROM taxonomy_term t, taxonomy_element te, taxonomy_baseterm bt WHERE bt.term = te.term and bt.base = %s and t.id = te.term and te.elem = %s ORDER BY t.weight, t.title"
    def terms(self, base_pk, element_pk): 
        '''
        Terms for a given element id, within a tree.
        The terms are ordered by weight and title, in that order.
        The return is  term model.
        
        @return [(id, title, slug, description)...] Full term models, ordered.
        '''
        c = connection.cursor()
        r = []
        #tpks = Element.objects.filter(base__exact=base_pk, elem__exact=element_pk).values_list('term', flat=True)
        #return Term.objects.filter(pk__in=tpks)
        try:
            c.execute(self._SQLElementTerms, [base_pk, element_pk])
            r = [e for e in c.fetchall()]
        finally:
            c.close()
        return r

      
# We want to 
# - de-typify the object connection
# : this is a database schema, so the connection must be of some type,
# so use Django's IntegerField pks.
# - Have a ManyToMany connection
# : may be enforced in some circumstances
# auto field handling should work ok here.
#! unwanted id field here
#! rename Elementent
#! node is unique per term? That willdo, not per tree.
#! must disallow duplicate pks on terms
class Element(models.Model):
    
    #tree = models.IntegerField(
      #db_index=True,
      #help_text="A Base associated with an element.",
      #)
      
    term = models.IntegerField(
      Term,
      help_text="A Term associated with an element.",
      )
      
    elem = models.IntegerField(
      db_index=True,
      help_text="An element associated with a Term.",
      )
  
    objects = models.Manager()
    system = ElementManager()
    
    def __str__(self):
      return "term({0})-{1}".format(
      self.term, 
      self.elem, 
      )
  
