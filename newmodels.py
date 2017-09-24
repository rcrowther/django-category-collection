from django.db import models
from django.core.urlresolvers import reverse
from django.db import connection

# Create your models here.


class TreeManager(models.Manager):
  def create(self, title, slug, description, is_single, weight):
      '''
      @param parents an array of pk
      '''
      # Make base term
      term = Term.system.create(self, treepk, parentpks=[-1], title, slug, description, weight):
      t = Tree(
          base=term.pk,
          is_single=is_single,
          is_unique=True,
          )
      t.save()
      return t  
        
  def update(self, pk, title, slug, description, is_single, weight):
      t = Tree( 
        pk=pk,
        title=title,
        slug=slug,
        description=description,
        is_single=is_single,
        is_unique=True,
        weight=weight
        )
      t.save()
      return t

  def delete(self, pk):
    # term data
    all_term_pks = list(Term.objects.filter(tree__exact=pk).values_list('pk', flat=True))

    # terms
    Term.objects.filter(tree__exact=pk).delete()

    # hierarchy
    TermParent.objects.filter(term__in=all_term_pks).delete()

    # elems
    Element.objects.filter(term__in=all_term_pks).delete()
    
    # tree
    Tree.objects.get(pk__exact=pk).delete() 
       
  _SQLIsSingle = "UPDATE taxonomy_tree SET is_single=%s  WHERE id = %s"
  def is_single(self, pk, is_single):
      '''
      Set parent status field.
      Silent operation.
      '''
      #! restore, when SQL is correct
      c = connection.cursor()
      try:
          c.execute(self._SQLIsSingle, [is_single, pk])
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
class Tree(models.Model):
  '''
  parent can be null, for top level. Therefore can be root also.
  '''
  base = models.IntegerField(
    db_index=True,
    help_text = "Root term in this tree",
  )
  
  is_single = models.BooleanField(
    default=True,
    help_text="Nunber of parents allowed for a term in the taxonomy (True = one only, False = many).",
    )
    
  is_unique = models.BooleanField(
    default=False,
    help_text="Nunber of parents allowed for a element in the taxonomy (True = one only, False = many).",
    )


  objects = models.Manager()
  system = TreeManager()

          
  def get_absolute_url(self):
    return reverse("tree-detail", kwargs={"slug": self.slug})

  def __str__(self):
    return "{0}".format(
    self.title, 
    )
    


class TermManager(models.Manager):
  
  def create(self, treepk, parentpks, title, slug, description, weight):
    t = Term( 
      tree=treepk,
      title=title,
      slug=slug,
      description=description,
      weight=weight
      )
      
    t.save()

    TermParent.system.merge(t.pk, parentpks)
    #if (isinstance(parents, list)):
        #TermParent.objects.bulk_create([TermParent(term=t.pk, parent=p) for p in parents])
    #else:
        #TermParent(
          #term=t.pk,
          #parent=parents
          #).save()

    return t


  def update(self, treepk, parents, termpk, title, slug, description, weight):
    #? no need for tree pk, never updated?
    t = Term(
      pk=pk, 
      tree=treepk,
      title=title,
      slug=slug,
      description=description,
      weight=weight
      )
      
    t.save()

    # update parents
    # remove originals
    TermParent.objects.filter(term__exact=termpk).delete()
    
    # react to lists of multiple parents
    if (isinstance(parents, list)):
        TermParent.objects.bulk_create([TermParent(term=t.pk, parent=p ) for p in parents])
    else:
        TermParent(
          term=pk,
          parent=parents
          ).save()
        
    return t


  #? Not taking advantage of the caches here?
  # do I care?
  def delete_recursive(self, pk):
    stash=[pk]
    while stash:
      tpk = stash.pop()
      children = TermParent.objects.filter(parent__exact=tpk).values_list('term', flat=True)
      
      for child_pk in children:
        parent_count = TermParent.objects.filter(term__exact=child_pk).count()
        # i.e the child has only one parent, this term, so stash
        # for removal
        if ( parent_count < 2 ):
          stash.append(child_pk)
                
      # delete the term
      Term.objects.get(pk__exact=tpk).delete()
      
      # delete any parents
      TermParent.objects.filter(term__exact=tpk).delete()
      
      # delete any parents
      Element.objects.filter(term__exact=tpk).delete()

  _SQLParents = "SELECT t.* FROM taxonomy_term t, taxonomy_termparent h WHERE h.term = %s and t.id = h.parent ORDER BY t.weight, t.title"
  def parents_ordered(self, pk):
      #'SELECT t.tid, t.* FROM {term_data} t INNER JOIN {term_hierarchy} h ON h.parent = t.tid WHERE h.tid = %d ORDER BY weight, name', 't', 'tid'), $tid);
      '''
      Parent/term pks for a given tree.
      The term pks are ordered by weight and title, in that order.
      NB: raw SQL query
      
      @return [(<all term info>)...]
      '''
      c = connection.cursor()
      try:
          c.execute(self._SQLParents, [pk])
          r = [e for e in c.fetchall()]
      finally:
          c.close()
      return r

  _SQLChildren = "SELECT t.* FROM taxonomy_term t, taxonomy_termparent h WHERE h.parent = %s and t.id = h.term ORDER BY t.weight, t.title"
  def children_ordered(self, pk):
      '''
      Parent/term pks for a given tree.
      The term pks are ordered by weight and title, in that order.
      NB: raw SQL query
      
      @return [(<all term info>)...]
      '''
      c = connection.cursor()
      try:
          c.execute(self._SQLChildren, [pk])
          r = [e for e in c.fetchall()]
      finally:
          c.close()
      return r

  _SQLTree = "SELECT tr.* FROM taxonomy_tree tr, taxonomy_term t WHERE tr.id = t.tree and t.id = %s"
  def tree(self, pk):
      '''
      Tree for given term
      '''
      c = connection.cursor()
      r = None
      try:
          c.execute(self._SQLTree, [pk])
          r = c.fetchone()
      finally:
          c.close()
      return r
      
      

class Term(models.Model):
    '''
    parent can be null, for top level. Therefore can be root also.
    '''
    # auto destruction and detection is nice. But so is manual insert.
    tree = models.IntegerField(
      db_index=True,
      help_text="A Tree associated with this Term.",
      )
      
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



class TermParentManager(models.Manager):

    def merge(self, termpk, parentpks):
        '''
        Create/update parents of a term.
        @param parentpks list of parentpks
        '''
        # no attempt made to check consistency of tree
        TermParent.objects.filter(term__exact=termpk).delete()
    
        # react to lists of multiple parents
        #if (isinstance(parents, list)):
        TermParent.objects.bulk_create([TermParent(term=termpk, parent=p) for p in parentpks])
        #else:
            #TermParent(
              #term=termpk,
              #parent=parentpks
              #).save()
          
          
    _SQLTermParentage = "SELECT h.term, h.parent FROM taxonomy_termparent h, taxonomy_term t WHERE t.tree = %s and t.id = h.term ORDER BY t.weight, t.title"
    #? not sure if this functional approach is best for Python,
    # but code is where it should be (could return a list...)
    def foreach_ordered(self, tree_pk, func):
      '''
      Parent/term pks for a given tree.
      The term pks are ordered by weight and title, in that order.
      
      @param func (term_id, parent_id) as raw fetchall.
      '''
      with connection.cursor() as c:
          c.execute(self._SQLTermParentage, [tree_pk])
          for e in c.fetchall():
            func(e)

    #! probably not fast, but unimportant?
    _SQLByTree = "SELECT h.* FROM taxonomy_termparent h, taxonomy_term t WHERE t.tree = %s and t.id = h.term"
    def multiple_to_single(self, tree_pk):
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
              c.execute(self._SQLByTree, [tree_pk])
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
# declared as ForeignKey.
#! unwanted id field here
class TermParent(models.Model):
    
  term = models.IntegerField(
    db_index=True,
    #editable=False,
    help_text="Term to connect to another Term.",
    )
    
  # can be null, if at root of taxonomy

  # Sadly, the autoincrement is dependent on underlying DB 
  # implementation. It would be nice to guarentee zero, but the only
  # way to do this is by an even more awkward method of migration.
  # So null it is, for unparented Terms. -1 sentinel is the compromise.
  parent = models.IntegerField(
    db_index=True,
    #null=True,
    #blank=True,
    help_text="Term parent for another term, or null for root (connection to self forbidden)",
    )

  #handy here and ther
  UNPARENT = -2
    
  # Now that would beggar belief, an auto-increment that allows -1...
  NO_PARENT = -1
  objects = models.Manager()
  system = TermParentManager()
  
  def __str__(self):
    return "{0}-{1}".format(
    self.term, 
    self.parent, 
    )
    
    
    
class ElementManager(models.Manager):
  _SQLCreate = "INSERT INTO taxonomy_termnode VALUES (null, %s, %s, %s)"
  #_SQLDeleteElement = "DELETE FROM taxonomy_termnode WHERE term_id = %s and elem = %s"
  def merge(self, term_pks, element_pk):
      '''
      Create/update element attachments to a Term.
      '''
      # no test for exists, delete then insert
      self.delete(tree_pk, [element_pk])
      c = connection.cursor()
      try:
          for tpk in term_pks:
              # terms know their trees, so lets keep the DB consistent
              tree_pk = Term.tree_pk()
              c.execute(self._SQLCreate, [tree_pk, tpk, element_pk])
      finally:
          c.close()

  def delete(self, tree_pk, element_pks):
      '''
      Remove this element from a tree 
      '''
      Element.objects.filter(tree__exact=tree_pk, elem__in=element_pks).delete()

  #? any need to order here?
  _SQLElementTerms = "SELECT t.* FROM taxonomy_term t, taxonomy_termnode WHERE t.id = term_id and tree = %s and elem = %s ORDER BY t.weight, t.title"
  def terms(self, tree_pk, element_pk): 
      '''
      Terms for a given element id, within a tree.
      The terms are ordered by weight and title, in that order.
      The return is full term model.
      
      @return [(<term>)...] Full term models, ordered.
      '''
      c = connection.cursor()
      r = []
      try:
          c.execute(self._SQLElementTerms, [tree_pk, element_pk])
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
  
  tree = models.IntegerField(
    db_index=True,
    help_text="A Tree associated with an element.",
    )
    
  # term is ForeignKey as it plays well with Django 'admin'.
  #not unique
  term = models.IntegerField(
    Term, 
    #on_delete=models.CASCADE,
    #db_index=True,
    help_text="A Term associated with an element.",
    )
    
  # Will not be unique. Nodes may be under several terms, and nodes
  # of different types share the same table.
  # must be integer, not Foreign key, as allows different types.
  #! how to delete?
  elem = models.IntegerField(
    db_index=True,
    help_text="An element associated with a Term.",
    )

  objects = models.Manager()
  system = ElementManager()
  
  def __str__(self):
    return "{0}-{1}-{2}".format(
    self.tree, 
    self.term, 
    self.elem, 
    )
