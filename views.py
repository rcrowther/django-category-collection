from django.shortcuts import render

# Create your views here.

from django.views.generic import ListView
from django.views.generic.detail import DetailView
from django.views.generic import TemplateView
from django.urls import reverse
from django.http import Http404
from django.utils import html
from django.utils.safestring import mark_safe
from itertools import chain

from .models import Term, Taxonomy, TermTaxonomy, TermTree

#from blunt_admin.views import ModelAdmin2
from django.http import HttpResponseRedirect



#from generictemplates import object_fields

#TODO:
# autoslug
# add delete action?
# check against options
# multi-step deletion?
# overview
# adjust Term to reflect tree source
# paginate
# reverse all redirects?
#? term list display indents
# consider redirects, and messages on term pages?

#class TaxonomyList(ListView):
#  context_object_name = 'taxonomy_list'
#  queryset = Term.objects.filter(parent__isnull=True)

#def taxonomy_list(request):
  #terms = Term.objects.filter(parent__isnull=True)
  #return render(request, 'taxonomy/taxonomy_list.html', {'taxonomy_list' : terms})

##def tree_view(request, slug):
  ##term = Term.objects.get(slug=slug)
  ##if(term.parent):
    ##raise Http404("Tree does not exist")
  ##return render(request, 'taxonomy/term_detail.html', {'term' : term})


#from django import forms

#class TreeListForm(forms.Form):
    #title = forms.CharField(label='title', max_length=100)
    #slug = forms.CharField(label='slug', max_length=100)
    
    
##from .forms import NameForm

#def treelist_view(request):
    ## if this is a POST request we need to process the form data
    #if request.method == 'POST':
        ## create a form instance and populate it with data from the request:
        #form = TreeListForm(request.POST)
        ## check whether it's valid:
        #if form.is_valid():
            ## process the data in form.cleaned_data as required
            ## ...
            ## redirect to a new URL:
            #return HttpResponseRedirect('/thanks/')

    ## if a GET (or any other method) we'll create a blank form
    #else:
        #form = TreeListForm()

    #return render(request, 'taxonomy/tree_list.html', {'form': form})

#from django.contrib.admin import helpers, widgets


#class TreeAddForm(forms.Form):
    #title = forms.CharField(label='title', max_length=100)
    #slug = forms.SlugField(label='slug', max_length=100)
    #is_single = forms.BooleanField(label='is single')
    #is_unique = forms.BooleanField(label='is unique')
    ##weight = forms.IntegerField(label='weight', max_value=3000, min_value=0, max_length=30)
    #weight = forms.IntegerField(label='weight')

#def treeadd_view(request):
    ## if this is a POST request we need to process the form data
    #if request.method == 'POST':
        ## create a form instance and populate it with data from the request:
        #form = TreeAddForm(request.POST)
        ## check whether it's valid:
        #if form.is_valid():
            ## process the data in form.cleaned_data as required
            ## ...
            ## redirect to a new URL:
            #return HttpResponseRedirect('/thanks/')

    ## if a GET (or any other method) we'll create a blank form
    #else:
        #form = TreeAddForm()

    #return render(request, 'taxonomy/tree_add.html', {'form': form})

########################################
## helpers

def tree_terms_for_element(tree_pk, pk):
  '''
  Get associated terms
  Ordered by weight.
  @return queryset of terms
  '''
  term_for_tree_ids = TermTaxonomy.objects.filter(taxonomy__exact=tree_pk).values_list('term', flat=True)
  term_ids = TermNode.objects.filter(node__exact=pk, term__in=term_for_tree_ids).values_list('term', flat=True)
  return Term.objects.order_by('weight').filter(pk__exact=term_ids)


def tree_term_titles(tree_pk):
  '''
  Get terms in a tree
  @return list of term data tuples (pk, title)
  '''
  term_pks = TermTaxonomy.objects.filter(taxonomy__exact=tree_pk)
  return Term.objects.filter(pk__in=term_pks).values_list('pk', 'title')
  
########################################
from django.forms import ModelForm


#########################################

from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator

csrf_protect_m = method_decorator(csrf_protect)

from django.contrib import messages
from django.db import models, router, transaction
from django.contrib.admin.utils import quote, unquote


        
def _term_delete(request, pk):
      app_label = Term._meta.app_label
      verbose_name = Term._meta.verbose_name

      # The object exists?
      try:
        o = Term.objects.get(pk__exact=pk)
      except Exception as e:
        # bail out to the main list
        msg = "{0} with ID '{1}' doesn't exist. Perhaps it was deleted?".format(
            Term._meta.verbose_name,
            unquote(pk)
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('tree-list'))

             
      if (request.method == 'POST'):
          # delete confirmed
  
          # retrieve the treepk
          # Passing the value through a form means using the template,
          # which is no fun.
          # This horrible retrieval may only be temporary. May remove
          # Django automanagement of the join tables?
          tt = None
          try:
            tt=TermTaxonomy.objects.get(term__exact=pk)
          except Exception as e:
            msg = "{0} for Term ID '{1}' is not registered? The database may not be coherent!".format(
                Taxonomy._meta.verbose_name,
                unquote(pk)
            )
            messages.add_message(request, messages.ERROR, msg)
            return HttpResponseRedirect(reverse('tree-list'))
            
          treepk=tt.taxonomy.pk
                    

          #print(str(treepk))
          #raise Exception
          
          #? logging
          #! deletion of descendants
          o.delete()
          #? model delete cascades seem to delete other table data for us.
          #tt = TermTaxonomy(taxonomy=tree, term=term)
          #tt.delete()
          #th = TermTree(term=term, parent=parent)
          #th.delete()
          
          msg = 'The {0} "{1}" was deleted'.format(verbose_name, o.title)
          messages.add_message(request, messages.SUCCESS, msg)
          redirect_url = reverse('term-list', args=[treepk])
          return HttpResponseRedirect(redirect_url)

      message = '<p>Are you sure you want to delete the Term "{0}"?</p><p>Deleting a term will delete all its term children if there are any. This action cannot be undone.</p><p>Deleting a term will not delete elements attached to the term</p>'.format(
      html.escape(o.title)
      )
      
      context={
        'title': 'Term Delete',
        'html_title': 'term_delete',
        'message': mark_safe(message),
        'action': '/taxonomy/term/{0}/delete/'.format(pk),
        'model_name': 'Term',
        'instance_name': html.escape(o.title),
      } 
      return render(request, 'taxonomy/delete_confirm_form.html', {'context': context})


#@csrf_protect_m        
def term_delete(request, pk):
  # Lock the DB. Found this in admin.
    with transaction.atomic(using=router.db_for_write(Term)):
      return _term_delete(request, pk)
  
    
    
##########################################
from .models import Term


#########################
# List of Tree Datas
# Also needs links to terms?

class TermListView(TemplateView):
  template_name = "taxonomy/generic_list.html"
  #?
  #context_object_name = 'term_list'

  def get_context_data(self, **kwargs):
      context = super(TermListView, self).get_context_data(**kwargs)
      #??? Need styling
      #messages.add_message(self.request, messages.INFO, "Totl duff")

      context['title'] = 'Term List'
      context['tools'] = mark_safe('<li><a href="/taxonomy/tree/{0}/term/add/" class="toollink"/>Add</a></li>'.format(context['treepk']))
      context['headers'] = mark_safe('<th>TITLE</th><th>SLUG</th><th>ACTION</th>')
      context['messages'] = messages.get_messages(self.request)
      #print('context:')
      #print(str(self.request))
      term_id_queryset = TermTaxonomy.objects.filter(taxonomy__exact=context['treepk']).values_list('term', flat=True)
      term_data_queryset = Term.objects.filter(pk__in=term_id_queryset).values_list('pk', 'title', 'slug')
      rows = []
      for m in term_data_queryset:
        row = '<td><a href="{0}">{1}</a></td><td>{2}</td><td><a href="{3}">delete</a></td>'.format(
          '/taxonomy/term/{0}/edit/'.format(m[0]),
          html.escape(m[1]),
          html.escape(m[2]),
          '/taxonomy/term/{0}/delete/'.format(m[0]),
          )
        rows.append(mark_safe(row))
      context['rows'] = rows
       
      return context

################


#! needs a tree? 
#class TermForm(ModelForm):
    ## need extra field for parent....
    ## and handle the treepk?
    #class Meta:
        #model = Term
        #fields = ['title', 'slug', 'weight']

from django import forms

#class TermSelectWidget(forms.Select):
    #def __init__(self, attrs=None, choices=()):
        #super().__init__(attrs, choices)
        ## choices can be any iterable, but we may need to render this widget
        ## multiple times. Thus, collapse it into a list so it can be consumed
        ## more than once.
        #self.term_data = Terms.objects.all().values_list('pk', 'titles')

    #need a render override        
        
#https://stackoverflow.com/questions/15795869/django-modelform-to-have-a-hidden-input
class TermForm(forms.Form):
    #? can auto-build parameters from the model?
    # prefilled and hidden, in any circumstance
    treepk = forms.IntegerField(max_value=100, widget=forms.HiddenInput())
    #? cache
    parent = forms.IntegerField(max_value=100, widget=forms.Select())
    #, widget=forms.Select(choices=current_termdata))

  #???slug field?
    title = forms.CharField(label='Title', max_length=64)
    slug = forms.SlugField(label='Slug', max_length=64)
    weight = forms.IntegerField(label='Weight', min_value=0, max_value=32767)
    #instance = None
    
    def __init__(self, *args, **kwargs):
      if ('instance' in kwargs):
        term = kwargs.pop('instance')
        kwargs['initial'] = self.model_to_dict(term)
        
      super().__init__(*args, **kwargs)
      #? cache
      # get potential parents.
      #treepk = kwargs['initial'].treepk if ('initial' in kwargs) else args[0]['treepk']
      #term_pks = TermTaxonomy.objects.filter(taxonomy__exact=self.treepk)
      #current_termdata = Term.objects.filter(pk__in=term_pks).values_list('pk', 'title')
      #print(str(self.fields['parent'].widget))
      #self.fields['parent'].widget.choices=current_termdata
      self.fields['parent'].widget.choices=tree_term_titles(1)
    
    # From ModelForm...
    def model_to_dict(self, instance):
        """
        Return a dict containing the data in ``instance`` suitable for passing as
        a Form's ``initial`` keyword argument.
    
        ``fields`` is an optional list of field names. If provided, return only the
        named.
    
        ``exclude`` is an optional list of field names. If provided, exclude the
        named from the returned dict, even if they are listed in the ``fields``
        argument.
        """
        opts = instance._meta
        data = {}
        for f in chain(opts.concrete_fields, opts.private_fields, opts.many_to_many):
            if not getattr(f, 'editable', False):
                continue
            data[f.name] = f.value_from_object(instance)
        return data
  


def term_add(request, treepk):
    url_base = '/taxonomy/term/'
  
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = TermForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            # URL base not working?
            #print( str(form.cleaned_data))
          #try:
            print(str(form.cleaned_data))
            
            #! catch repeated terms?
            #! catch circular references?
            
            # get the validated data
            d = form.cleaned_data.copy()
            
            # remove our extra form items
            treepk = d.pop('treepk')
            parentpk = d.pop('parent')
            print('treepk, parent:')
            print(str(treepk))
            print(str(parentpk))
            #Term(slug= 'walks', title= 'walks', weight= 1)

            #! Shambolic, expensive query and writing?
            term = Term(**d)            
            term.save()
            tree=Taxonomy.objects.get(pk=treepk)
            parent=Term.objects.get(pk=parentpk)
            #print('newid:')
            #print(new_pk)
            tt = TermTaxonomy(taxonomy=tree, term=term)
            tt.save()
            th = TermTree(term=term, parent=parent)
            th.save()
            #            order = form.save(commit=false)
            return HttpResponseRedirect('/taxonomy/term/{0}'.format(form.cleaned_data['slug']))
          #except ValueError:
        else:
            raise Http404("Term failed to validate")  
    else:
        # unbound
        # but bind with treepk... but this produces errors?
        #form = TermForm({'treepk': treepk})
        form = TermForm(initial={'treepk': treepk})
        #form = TermForm(treepk=treepk)
        context={
        'form': form,
        'title': 'Term Add',
        'html_title': 'term_add',
        'action': '/taxonomy/tree/{0}/term/add/'.format(treepk),
        'action_title': 'Save',
        }    
    return render(request, 'taxonomy/generic_form.html', {'context': context})
    
    
    
def term_edit(request, pk):
    url_base = '/taxonomy/term/{0}'.format(pk)
    ## if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and validate
        a = Term.objects.get(pk=pk)
        f = TermForm(request.POST, instance=a)
        try:
          if (not f.is_valid()):
            #! where do validation errors get stored?
            #! this should be an error list?
            msg = "Term failed to validate?"
            #.format(
            #    Taxonomy._meta.verbose_name,
            #)
            messages.add_message(request, messages.ERROR, msg)
            #return HttpResponseRedirect(reverse('tree-list'))
          else:
            # valid
            print('cleaned data:')
            print(str(f.cleaned_data))
            # cleaned data and make an object
            t=Term(
              title=f.cleaned_data['title'],
              slug=f.cleaned_data['slug'],
              weight=f.cleaned_data['weight'],
              )
            t.save()
            
            # Should use this?
            new_pk=t.pk
            
            #? Not Allowed?
            #if (f.fields['treepk'].has_changed()):
            #  TermTree(
            #    parent=f.cleaned_data['treepk'],
            #    term=t
            #    )
            
            if (f.fields['parent'].has_changed()):
              delete_set= TermTaxonomy.objects.filter(exact=new_pk)
              delete_set.delete()
              
              o = TermTaxonomy(
                term=t,
                taxonomy=f.cleaned_data['treepk'],
                )
                
              o.save()

            msg = 'Term "{0}" was updated'.format(t.title)
            messages.add_message(request, messages.SUCCESS, msg)
            
          return HttpResponseRedirect('/taxonomy/tree/{0}/list'.format(f.fields['treepk']))
        except ValueError:
          raise Http404("Term failed to validate")          
        #form = TermForm(request.POST)
        ## check whether it's valid:
        #if form.is_valid():
            ## process the data in form.cleaned_data as required

            #term = Term(
            #)
            ## redirect to a new URL:
            ## URL base not working?
            #print( str(form.cleaned_data))
            
            #return HttpResponseRedirect('/taxonomy/term/{0}'.format(request.POST['slug']))
    else:
        # get the object
        #? protect
        term = Term.objects.get(pk=pk)
        form = TermForm(instance=term)
        
    context={
    'form': form,
    'title': 'Term Edit',
    'html_title': 'term_edit|' + str(pk),
    'action': url_base + '/edit/',
    'action_title': 'Save',
    }
    
    return render(request, 'taxonomy/generic_form.html', {'context': context})

#########################
def _tree_delete(request, pk):
      #? into is all similar - DRY
      #? Post is different
      app_label = Taxonomy._meta.app_label
      verbose_name = Taxonomy._meta.verbose_name

      
      # The object exists?
      try:
        o = Taxonomy.objects.get(pk__exact=pk)
      except Exception as e:
        # bail out to the main list
        msg = "{0} with ID '{1}' doesn't exist. Perhaps it was deleted?".format(
            'Tree',
            unquote(pk)
        )
        messages.add_message(request, messages.WARNING, msg) 
        return HttpResponseRedirect(reverse('tree-list'))


             
      if (request.method == 'POST'):
          # delete confirmed
                    
          #print(str(treepk))
          #raise Exception
          
          #? logging
          # deletion...
          # ...tree
          o.delete()
          
          # ...term associations
          term_ids = TermTaxonomy.objects.filter(taxonomy__exact=pk)
          #, term=term)
          term_ids.delete()
          
          # ...term hierarchy
          #? no need to check parents too
          tree_hierarchy = TermTree.objects.filter(term__in=term_ids)
          tree_hierarchy.delete()
          
          # ...terms
          terms = Term.objects.filter(pk__in=term_ids)
          terms.delete()
          
          msg = 'The {0} "{1}" was deleted'.format(verbose_name, o.title)
          messages.add_message(request, messages.SUCCESS, msg)
          redirect_url = reverse('tree-list')
          return HttpResponseRedirect(redirect_url)

      message = '<p>Are you sure you want to delete the Tree "{0}"?</p><p>Deleting a tree will delete all its term children if there are any. This action cannot be undone.</p><p>(deleting a tree will not delete elements attached to the terms</p>'.format(
      html.escape(o.title)
      )
      
      context={
        'title': 'Tree Delete',
        'html_title': 'tree_delete',
        'message': mark_safe(message),
        'action': '/taxonomy/tree/{0}/delete/'.format(pk),
        'model_name': 'Taxonomy',
        'instance_name': html.escape(o.title),
      } 
      return render(request, 'taxonomy/delete_confirm_form.html', {'context': context})


#@csrf_protect_m        
def tree_delete(request, pk):
    # Lock the DB. Found this in admin.
    #? lock what? How?
    with transaction.atomic(using=router.db_for_write(Taxonomy)):
      return _tree_delete(request, pk)
      
#########################
# List of Tree Datas
# Also needs links to terms?

class TaxonomyListView(TemplateView):
  template_name = "taxonomy/generic_list.html"
  #context_object_name = 'tree_list'

  def get_context_data(self, **kwargs):
      context = super(TaxonomyListView, self).get_context_data(**kwargs)
      #queryset = Term.objects.filter(parent__isnull=True)
      context['title'] = 'Tree List'
      context['tools'] = mark_safe('<li><a href="/taxonomy/tree/add/" class="toollink"/>Add</a></li>')
      context['headers'] = mark_safe('<th>TITLE</th><th>SLUG</th><th>ACTION</th><th></th>')
      context['messages'] = messages.get_messages(self.request)

      rows = []
      tree_queryset = Taxonomy.objects.all().values_list('pk', 'title', 'slug')

      for m in tree_queryset:
        row = '<td><a href="{0}">{1}</a></td><td>{2}</td><td><a href="{3}">list terms</a></td><td><a href="{4}">delete</a></td>'.format(
          '/taxonomy/tree/{0}/edit/'.format(m[0]),
          html.escape(m[1]),
          html.escape(m[2]),
          '/taxonomy/tree/{0}/term/list/'.format(m[0]),
          '/taxonomy/tree/{0}/delete/'.format(m[0]),
          )
        rows.append(mark_safe(row))
      context['rows'] = rows
       
      return context

################
class TreeForm(ModelForm):
    class Meta:
        model = Taxonomy
        fields = ['title', 'slug', 'is_single', 'is_unique', 'weight']
        

#! add 'parent' field
def tree_add(request):
    url_base = '/taxonomy/tree/'
  
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        #form = TermForm(request.POST)
        # check whether it's valid:
        #if form.is_valid():
            # process the data in form.cleaned_data as required
            # ...
            # redirect to a new URL:
            # URL base not working?
            #print( str(form.cleaned_data))
        f = TreeForm(request.POST)
        try:
          f.save()
          return HttpResponseRedirect('/taxonomy/tree/{0}'.format(request.POST['slug']))
        except ValueError:
          raise Http404("Tree failed to validate")  
    else:
        form = TreeForm()
        context={
        'form': form,
        'title': 'Tree Add',
        'html_title': 'tree_add',
        'action': '/taxonomy/tree/add/',
        'action_title': 'Save',
        }    
    return render(request, 'taxonomy/generic_form.html', {'context': context})
    
    
def tree_edit(request, pk):
    url_base = '/taxonomy/tree/{0}'.format(pk)
    ## if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        a = Taxonomy.objects.get(pk=pk)
        f = TreeForm(request.POST, instance=a)
        try:
          #! defo a an update?
          #? runs validate?
          f.save()
          
          msg = 'Tree "{0}" was updated'.format(f.cleaned_data['title'])
          messages.add_message(request, messages.SUCCESS, msg)
            
          return HttpResponseRedirect('/taxonomy/tree/{0}/list'.format(f.cleaned_data['pk']))
        except ValueError:
          #! dont we display errors?
          raise Http404("Tree data failed to validate")          
        #form = TermForm(request.POST)
        ## check whether it's valid:
        #if form.is_valid():
            ## process the data in form.cleaned_data as required

            #term = Term(
            #)
            ## redirect to a new URL:
            ## URL base not working?
            #print( str(form.cleaned_data))
            
            #return HttpResponseRedirect('/taxonomy/term/{0}'.format(request.POST['slug']))

    # if a GET (or any other method) we'll create a blank form
    else:
        #? protect
        o = Taxonomy.objects.get(pk=pk)
        form = TreeForm(instance=o)
        
    context={
    'form': form,
    'title': 'Tree Edit',
    'html_title': 'tree_edit|' + str(pk),
    'action': url_base + '/edit/',
    'action_title': 'Save',
    }
    
    return render(request, 'taxonomy/generic_form.html', {'context': context})