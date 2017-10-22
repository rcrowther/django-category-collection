from django.shortcuts import render


from .models import Term #, Base, TermParent, BaseTerm, Element



# TODO:

## Models
# how big is that pk field?
# check SQL queries
# SQL commits and transactions?
# do more generators in the manager SQL, they seem natural
#x refactor NOPARENT to NO_PARENT

## cache
#x bases needs a similar api to term and count

## admin
# paginate lists
# test permissions admin, still not happy
# maybe not parent to root when is root?
# break the admin down


## widgets
# make weight to zero button

## template
# clearup the overcooked js
# tidy messy, wet templates
# generictemplate module detection

## forms
#x consider FormViews for everything. 
# Compare against adminForms, which seem to have more input protection
# do the transaction thing on all deletes...
# from django.db import models, router, transaction
# ...and consider csrf  
#from django.views.decorators.csrf import csrf_protect
#from django.utils.decorators import method_decorato  
#csrf_protect_m = method_decorator(csrf_protect)

## fields/widgets
# make a stub field, now you've decided they all need replacing
# writeup on widget swapping
#x fancy term widget? SVG?

## usage
# convert code to new API


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


#http://127.0.0.1:8000/taxonomy/term_titles_ajax/29/
def term_title_search_view(request, base_pk):
    tl = None
    if request.method == 'GET':
        tl = list(Term.system.title_search(base_pk, request.GET.get('search')))
    return JsonResponse(tl, safe=False)
