import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _, ngettext_lazy
from django.forms import IntegerField, TypedChoiceField, TypedMultipleChoiceField
from .widgets import IDTitleAutocompleteInput


#! could use a cute initializer of (id,  title)?
class IDTitleAutocompleteField(IntegerField):
    '''
    Field that validates a value made of a string with an id/pk embedded.
    The field inherits from IntegerField, and mostly behaves like an 
    IntegerField. However, the field is capable of displaying descriptive 
    data with the integer. It strips the data to validate and return a 
    clean integer. 
    The field is equiped with an extra set of code which assumes the 
    machinery for recovering descriptive code is AJAX.    
    '''
    widget = IDTitleAutocompleteInput
    # set this, the integer is intended as an id
    min_value = 0
    default_error_messages = {
        'invalid': _('Enter a value from autocomplete.'),
    }
    re_extract = re.compile(r'\((\d+)\)')


    def __init__(self, *args, ajax_href=None, max_value=None, **kwargs):
        super().__init__(*args, max_value=max_value, **kwargs)
        self.ajax_href = ajax_href

    def _get_ajax_href(self):
        return self._ajax_href

    def _set_ajax_href(self, value):
        # Setting ajax_href also sets the ajax_href on the widget.
        self._ajax_href = self.widget.ajax_href = value

    ajax_href = property(_get_ajax_href, _set_ajax_href)

    # for what? is this where we should do this?
    #def prepare_value(self, value):
        #if isinstance(value, datetime.datetime):
            #value = to_current_timezone(value)
        #return value
        
    def to_python(self, value):
        """
        Strip for a number, then validate the number.
        """              
        # get the number
        m = self.re_extract.search(value)
        if (m is None):
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        value = m.group(1)
        return super().to_python(value)

#! unecessary. use choices()
#class TermField(TypedMultipleChoiceField):
    #'''
    #Handle taxonomy terms.
    #The one and only outstanding feature is that the Field requires a
    #tree ID to filter terms offered. This property is set on 
    #contained widgets (which must enable the property).
    #@param tree_pk tree to offer terms from 
    #'''
    #def __init__(self, tree_pk, *args, **kwargs):
        #super().__init__(*args, coerce=lambda val: int(val), **kwargs)
        #self.tree_pk = tree_pk
        
    #def _get_tree_pk(self):
        #return self._tree_pk

    #def _set_tree_pk(self, value):
        ## Setting ajax_href also sets the ajax_href on the widget.
        #self._tree_pk = self.widget.tree_pk = value

    #tree_pk = property(_get_tree_pk, _set_tree_pk)


#class TaxonomySingleTermField(forms.TypedChoiceField):
    #'''
    #A field which only accepts
    #A lightly customized field for vali
    #'''
    #def __init__(self, tree_pk, *args, **kwargs):
        #super().__init__(choices=partial(term_list, tree_pk), *args, coerce=lambda val: int(val), empty_value=-1, **kwargs)

    #def valid_value(self, value):
        #print('valid value')
        #super().valid_value(value) 

class TaxonomyTermField(TypedMultipleChoiceField):
    '''
    A field to establish element connections to a term in a taxonomy.
    Light adaption establishes a few defaults.
    '''
    empty_value = -1
    required = False
    label='Taxonomy',
    help_text="Choose a term to parent this item"
    def __init__(self, *args, **kwargs):
        #super().__init__(*args, coerce=lambda val: [int(v) for v in val], **kwargs)
        super().__init__(*args, coerce=lambda val: val, **kwargs)

