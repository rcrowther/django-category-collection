from django.db import models
from django.core.urlresolvers import reverse

# Create your models here.


class TreeManager(models.Manager):

    
  def delete(self, pk):
    # term data
    all_term_pks = list(Term.objects.filter(tree__exact=pk).values_list('pk', flat=True))

    # terms
    Term.objects.filter(tree__exact=pk).delete()

    # hierarchy
    TermParent.objects.filter(term__in=all_term_pks).delete()

    # nodes
    #!
    
    # tree
    Tree.objects.get(pk__exact=pk).delete() 
       
        
        
        
        
#? names and slugs do not have to be unique, as we may want to 
# structure a website, for example, and there may be several 'news'
# terms under 'sports', 'local', 'culture' etc.
# On the other hand, that means slugs can not be used for URLs. 
# It seems ok to enforce uniqueness within a term, but this is not the
# place for that.
#? That means a unique identifier from the data could be parent-term? 
  
# We do want an id field here
class Tree(models.Model):
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
    # unique specifies index
    #db_index=True,
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
    help_text="Nunber of parents allowed for a node in the taxonomy (True = one only, False = many).",
    )
    
  weight = models.PositiveSmallIntegerField(
    blank=True,
    default=0,
    db_index=True,
    help_text="Priority for display in some templates. Lower value orders first. 0 to 32767.",
    )


  objects = models.Manager()
  system = TreeManager()
  
  
  #def save(self, *args, **kwargs):
    #super(Tree, self).delete(*args, **kwargs) 
    
 
        
          
  def get_absolute_url(self):
    return reverse("tree-detail", kwargs={"slug": self.slug})

  def __str__(self):
    return "{0}".format(
    self.title, 
    )
    


class TermManager(models.Manager):


  def create(self, treepk, parents, title, slug, description, weight):
    t = Term( 
      tree=treepk,
      title=title,
      slug=slug,
      description=description,
      weight=weight
      )
      
    t.save()

    # set parents
    #! Right now, only hammering single parent in?
    TermParent(
      term=t.pk,
      parent=parents
      ).save()

    return t


  def update(self, treepk, parents, pk, title, slug, description, weight):
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
    #! Right now, only hammering single parent in?
    TermParent.objects.filter(term__exact=pk).delete()
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
      
      #! delete node connections
          
      # delete the term
      Term.objects.get(pk__exact=tpk).delete()
      
      # delete any parents
      TermParent.objects.filter(term__exact=tpk).delete()
    
    

  
#! not to self?
#! node too general
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
    
  # Not unique. Terms may be in different taxonomies
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

  #@property
  #def children(self):
    ##? this a special manager?
    #return self.term_set.all()

  #@property
  #def trees(self):
    ##? this a special manager?
    #return self.objects.filter(parent__isnull=True)


  
  #def save(self, *args, **kwargs):
    #super(Term, self).delete(*args, **kwargs) 
    
     
  def get_absolute_url(self):
    return reverse("term-detail", kwargs={"slug": self.slug})

  def __str__(self):
    return "{0}".format(
    self.title, 
    )

# Separate the heirarchy associations
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
  #term = models.ForeignKey(
    #Term, 
    #on_delete=models.CASCADE,
    #db_index=True,
    #related_name='+',
    ##related_name="children",
    ##related_query_name="children",
    ##editable=False,
    #help_text="Term to connect to another Term",
    #)
    
  term = models.IntegerField(
    db_index=True,
    #editable=False,
    help_text="Term to connect to another Term.",
    )
    
  # can be null, if at root of taxonomy
  #parent = models.ForeignKey(
    #Term, 
    #on_delete=models.CASCADE,  
    #blank=True, 
    #null=True,
    #db_index=True,
    #related_name='+',
    ##related_name="children",
    ##related_query_name="children",
    ##editable=False,
    #help_text="Term parent for another term, or null for root (connection to self forbidden)",
    #)

  # Sadly, the autoincrement is dependent on underlying DB 
  # implementation. It would be nice to guarentee zero, but the only
  # way to do this is by an even more awkward method of migration.
  # So null it is, for unparented Terms.
  parent = models.IntegerField(
    db_index=True,
    #null=True,
    #blank=True,
    help_text="Term parent for another term, or null for root (connection to self forbidden)",
    )
    
  # Now that would beggar belief, an auto-increment tat allows -1...
  NO_PARENT = -1

  def save(self, *args, **kwargs):
    # Raise on circular reference
    #! can be prevented in admin? Limited list?
    #parent_term = self.parent
    # climb the ancestory to check...
    #while parent_term is not None:
    #    if parent_term == self.term:
    #        raise RuntimeError("Disallowed: Parent joined to self/circular reference.")
    #    parent_term = self.objects.get(term__exact=parent_term.pk).parent

    super(TermParent, self).save(*args, **kwargs)

  def __str__(self):
    return "{0}-{1}".format(
    self.term, 
    self.parent, 
    )
    


# We want to 
# - de-typify the object connection
# : this is a database schema, so the connection must be of some type,
# so use Django's IntegerField pks.
# - Have a ManyToMany connection
# : may be enforced in some circumstances
# auto field handling should work ok here.
#! unwanted id field here
class TermNode(models.Model):
  term = models.ForeignKey(
    Term, 
    on_delete=models.CASCADE,
    db_index=True,
    help_text="A Term associated with an element.",
    )
    
  # Will not be unique. Nodes may be under several terms, and nodes
  # of different types share the same table.
  # must be integer, not Foreign key, as allows different types.
  #! how to delete?
  node = models.IntegerField(
    db_index=True,
    help_text="An element associated with a Term.",
    )

  def __str__(self):
    return "{0}-{1}".format(
    self.term.title, 
    self.node, 
    )
