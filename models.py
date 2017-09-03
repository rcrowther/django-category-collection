from django.db import models
from django.core.urlresolvers import reverse

# Create your models here.

# We need this because we want to 
# - de-typify the object connection
# - Have a ManyToMany connection
#class TermElement(models.Model):
  #parent = models.OneToOneField(
    #'Term', 
    #on_delete=models.CASCADE,  
    ##related_name="children",
    ##related_query_name="children",
    #help_text="Connect to another node, or null (cconnection to self forbidden)",
    #)
    
  #term = models.OneToOneField(
    #'Term', 
    #on_delete=models.CASCADE,  
    ##related_name="children",
    ##related_query_name="children",
    #help_text="Connect to another node, or null (cconnection to self forbidden)",
    #)

#class TermParent(models.Model):
  #parent = models.ForeignKey(
    #'Term', 
    #on_delete=models.CASCADE,  
    ##related_name="children",
    ##related_query_name="children",
    #help_text="Connect to another node, or null (cconnection to self forbidden)",
    #)
    
  #term = models.ForeignKey(
    #'Term', 
    #on_delete=models.CASCADE,  
    ##related_name="children",
    ##related_query_name="children",
    #help_text="Connect to another node, or null (cconnection to self forbidden)",
    #)

class Taxonomy(models.Model):
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
    help_text="Priority for display in some templates. Lower value orders first. 0 to 32767.",
    )

  def __str__(self):
    return "{0}".format(
    self.title, 
    )
    
# Separate this as we will often want to know
# the allowable nodes on a term, without other Taxonomy data
class TaxonomyNodetype(models.Model):
  taxonomy = models.OneToOneField(
    Taxonomy,
    models.CASCADE,
    primary_key=True,
    #editable=False,
    help_text="Type of data allowed in the Taxonomy.",
    )
  
  node_type = models.CharField(
    max_length=255,
    db_index=True,
    #editable=False,
    help_text="Type of data allowed in the Taxonomy.",
    )     


#! not to self?
#! node too general
class Term(models.Model):
  '''
  parent can be null, for top level. Therefore can be root also.
  '''
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

  weight = models.PositiveSmallIntegerField(
    blank=True,
    default=0,
    help_text="Priority for display in some templates. Lower value orders first. 0 to 32767.",
    )

  #@property
  #def children(self):
    ##? this a special manager?
    #return self.term_set.all()

  #@property
  #def trees(self):
    ##? this a special manager?
    #return self.objects.filter(parent__isnull=True)
    
  def get_absolute_url(self):
    return reverse("term-detail", kwargs={"slug": self.slug})
    #return reverse(views.TermDetailView, kwargs={"slug": self.slug})

  def __str__(self):
    return "{0}".format(
    self.title, 
    )

# Separate the heirarchy associations
# Terms may link to several parents
# in a multi taxonomy
class TermTree(models.Model):
  term = models.ForeignKey(
    Term, 
    on_delete=models.CASCADE,
    db_index=True,
    related_name='+',
    #related_name="children",
    #related_query_name="children",
    #editable=False,
    help_text="Term to connect to another Term",
    )
    
  # can be null, if taxonomy root
  parent = models.ForeignKey(
    Term, 
    on_delete=models.CASCADE,  
    blank=True, 
    null=True,
    db_index=True,
    related_name='+',
    #related_name="children",
    #related_query_name="children",
    #editable=False,
    help_text="Term parent for another term, or null for root (connection to self forbidden)",
    )

    
  def save(self, *args, **kwargs):
    # Raise on circular reference
    #! can be prevented in admin? Limited list?
    #parent_term = self.parent
    # climb the ancestory to check...
    #while parent_term is not None:
    #    if parent_term == self.term:
    #        raise RuntimeError("Disallowed: Parent joined to self/circular reference.")
    #    parent_term = self.objects.get(term__exact=parent_term.pk).parent

    super(TermTree, self).save(*args, **kwargs)

  def __str__(self):
    return "{0}-{1}".format(
    self.term.title, 
    self.parent.title, 
    )
    
# Associate Terms with a Taxonomy
class TermTaxonomy(models.Model):
  term = models.OneToOneField(
    Term,
    on_delete=models.CASCADE,
    primary_key=True,
    #editable=False,
    help_text="A Term associated with a Taxonomy.",
    )
    
  taxonomy = models.ForeignKey(
    Taxonomy, 
    on_delete=models.CASCADE,
    db_index=True,
    #editable=False,
    help_text="A Taxonomy associated with a Term.",
    )
    
    #? method for all terms for a tree?
  def __str__(self):
    return "{0}-{1}".format(
    self.term.title, 
    self.taxonomy.title, 
    )
    
# We need to associate many nodes with each term
# element, not node
class TermNode(models.Model):
  term = models.ForeignKey(
    Term, 
    on_delete=models.CASCADE,
    db_index=True,
    #editable=False,
    help_text="A Term associated with an element.",
    )
    
  # Will not be unique. Nodes may be under several terms, and nodes
  # of different types share the same table.
  # must be integer, not Foreign key, as allows different types.
  #! how to delete?
  node = models.IntegerField(
    db_index=True,
    #editable=False,
    help_text="Id of an element associated with a Term.",
    )

