'''
Handle taxonomy container elements within forms
'''

from .models import TermParent, Element
from .api import terms_flat_tree, element_terms, base

def term_choices(base_pk):
    '''
    Term data formatted for HTML selectors.
    Term pks from the tree. For general term parenting.
    
    @return list of (pk, title) from a tree.
    '''
    ftree = terms_flat_tree(base_pk)
    b = [(TermParent.UNPARENT, '<not attached>')]
    [b.append((t.pk, ('-' * t.depth) + t.title)) for t in ftree]
    return b


def term_choice_value(base_pk, model_instance):
    '''
    Value to be used in a multiple select button
    @return if instance is none, or a search for existing attached terms
    returns empty, then [TermParent.UNPARENT], else [instance_parent_pk, ...]
    '''
    if (model_instance is None):
        return [TermParent.UNPARENT]
    else:
        xt = element_terms(base_pk, model_instance.pk)
        if (not xt):
            return [TermParent.UNPARENT]
        return [t[0] for t in xt]


def form_set_select(form, taxonomy_field_name, base_pk, instance):
    assert base(base_pk) is not None, "base_pk can not be found: base_pk:{0}".format(base_pk)
    form.fields[taxonomy_field_name].choices = term_choices(base_pk)
    form.initial[taxonomy_field_name] = term_choice_value(base_pk, instance)
        
        
def save(form, taxonomy_field_name, base_pk, obj):
    assert base(base_pk) is not None, "base_pk can not be found: base_pk:{0}".format(base_pk)
    taxonomy_terms = form.cleaned_data.get(taxonomy_field_name)
    if(taxonomy_terms is None):
        raise KeyError('Unable to find clean data for taxonomy parenting: field_name : {0}'.format(base_pk))
    if ('-2' in taxonomy_terms):
        Element.system.delete(base_pk, obj.pk)
    else:
        Element.system.merge(taxonomy_terms, obj.pk)

def remove(base_pk, obj):
    assert base(base_pk) is not None, "base_pk can not be found: tree_pk:{0}".format(base_pk)
    Element.system.delete(base_pk, obj.pk) 
