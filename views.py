from django.shortcuts import render


#from django.views.generic import ListView
#from django.views.generic.detail import DetailView
#from django.views.generic import TemplateView
#from django.urls import reverse
#from django.http import Http404, HttpResponseRedirect
#from django.utils import html
#from django.utils.safestring import mark_safe
#from django.views.decorators.cache import never_cache
#from django.db import connection
#from itertools import chain
#from functools import partial
#import sys
#from collections import namedtuple

from .models import Term, Base, TermParent, BaseTerm, Element
from .cache import term_descendant_pks, terms_flat_tree, base



# TODO:
# Some url solution
# how big is that pk field?
# bulk add/delete (nodes and terms especially)
# check actions
# check nodes
#x check weights
# access methods
# have at look at SQL queries
# SQL commits and transactions?
# paginate
#x multiparents
#x protect form fails
# test permissions admin
# generictemplate module detection
# set weight to zero button
# maybe not parent to root when is root?
#x treelist is duplicating
#clearup the overcooked js

    
from django.forms import TypedChoiceField, TypedMultipleChoiceField
#!
# isn't this for elements? So shouldn't default be -2?
def term_form_field_select(base_pk):
    '''
    @return a single or multi-selector field with all-term widget
    '''
        # return differnt kinds of fields depening if this is a 
        # multiparent taxonomy or not
    t = base(base_pk)
    choices = term_choices(base_pk)
    if (t.is_single()):
      return TypedChoiceField(
      choices = choices,
      coerce=lambda val: int(val), 
      empty_value=-1,
      label='Taxonomy',
      help_text="Choose a term to parent this item"
      )
    else:
      return TypedMultipleChoiceField(
      choices = choices,
      coerce=lambda val: int(val), 
      empty_value=-1,
      label='Taxonomy',
      help_text="Choose a term to parent this item"
      )

  
########################################
## views

#from django.forms import ModelForm

#from django.views.decorators.csrf import csrf_protect
#from django.utils.decorators import method_decorator

#csrf_protect_m = method_decorator(csrf_protect)

#from django.contrib import messages
#from django.db import models, router, transaction







################

#from django import forms

     
#from django.forms import TypedMultipleChoiceField, MultipleChoiceField
#from django.forms.fields import CallableChoiceIterator

import json
from django.http import JsonResponse
from django.views import View

#! extend with extra descriptions
#!test they exist
#! add a queryset. or pk set?
def GenericTitleSearchJSONView(model1, title_field1, case_insensitive1=True):
    class GenericTitleSearchJSONView(View):
        model = model1
        title_field = title_field1
        case_insensitive = case_insensitive1
    
        def get(self, request, *args, **kwargs):
            tl = None
            pattern = request.GET.get('search')
            if (pattern is not None):
                if (self.case_insensitive):
                    tl = list(self.model.objects.filter(title__istartswith=pattern).values_list('pk', self.title_field))
                else:
                    tl = list(self.model.objects.filter(title__startswith=pattern).values_list('pk', self.title_field))
            else:
                tl = list(self.model.objects.all().values_list('pk', self.title_field))
            return JsonResponse(tl, safe=False)
    return GenericTitleSearchJSONView


#? could use base_term_pks from cache ?
#http://127.0.0.1:8000/taxonomy/term_titles_ajax/29/
def term_title_search_view(request, base_pk):
    tl = None
    if request.method == 'GET':
        tl = list(Term.system.title_search(base_pk, request.GET.get('search')))
    return JsonResponse(tl, safe=False)
