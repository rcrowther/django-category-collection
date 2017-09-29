from django import forms

from django.core.exceptions import ImproperlyConfigured
from .fields import IDTitleAutocompleteField, TaxonomyTermField
#from .widgets import IDTitleAutocompleteInput


      

 

# defined element, with title?, variable taxonomy by select, or by search, or by display?
def modelform_factory(model, treepk, toLabel=None):
    '''
    Returns a simple form suitable for registering model instances as
    elements in a taxonomy.
    '''
    # get the id
    pk_name = model._meta.pk.name
    #raise ImproperlyConfigured('no id field found: model:{0}'.format(html.escape(model._meta.verbose_name))) 
    return  ModelTreeForm(treepk)
###

class ElementSearchForm(forms.Form):
    #pk = forms.IntegerField(label='Element Id', min_value=0,
      #help_text="Id of an element to be categorised."
      #)
      
    title = IDTitleAutocompleteField(
      ajax_href='/taxonomy/term_titles/29',
      label='Element ID/Title', 
      help_text="Title of an element to be categorised."
      )

    def __init__(self, tree_pk, *args, **kwargs):
      super().__init__(*args, **kwargs)

###################




