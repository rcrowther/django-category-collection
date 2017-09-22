from django import forms



class ElementForm(forms.Form):
    '''
    Associate elements with taxonomy terms
    '''
    #! block edit on both below
    term_pk = forms.IntegerField(label='Term id', min_value=0,
      disabled=True,
      help_text="Id of a category for an element."
      )
      
    title = forms.CharField(label='Term Title', max_length=64,
      disabled=True,
      help_text="Name of the category. Limited to 255 characters."
      )
      
    element_pk = forms.IntegerField(label='Element Id', min_value=0,
      help_text="Id of an element to be categorised."
      )
      
    def __init__(self, *args, **kwargs):
      super().__init__(*args, **kwargs)
 

# defined element, with title?, variable taxonomy by select, or by search, or by display?
def modelform_factory(model, treepk, toLabel=None):
    '''
    Returns a simple form suitable for registering model instances as
    elements in ataxonomy.
    '''
    # get the id
    pk_name = model._meta.pk.name
    #raise ImproperlyConfigured('no id field found: model:{0}'.format(html.escape(model._meta.verbose_name))) 
    return  ModelTreeForm(treepk)
###

