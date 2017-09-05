from django.contrib import admin
from django import forms


# Register your models here.


from .models import Term, Tree, TermTree, TermParent, TermNode


#class TaxonomySelectField(forms.ChoiceField):
#  default = '0'
#  choices = [('0', 'Main site'),('1', 'emails')]


#! should remove the present item?
class TaxonomySelectField(forms.ModelChoiceField):
  '''
  Select box containing available taxonomies
  '''
  #! When we know the choice of none is not possible
  #empty_label = None
  
  def __init__(self, level_indicator='-', *args, **kwargs):
    self.level_indicator = level_indicator
    super(TaxonomySelectField, self).__init__(queryset=Tree.objects.all())

  def label_from_instance(self, obj):
    """
    Creates labels which represent the tree level of each node when
    generating option labels.
    """
    return '%s %s' % (self.level_indicator * 1, obj.title)


#! should remove the present item?
#class TermSelectField(forms.ModelChoiceField):
  #'''
  #Select box containing terms from a taxonomy
  #'''
  ## When we know the choice of none is not possible
  ##empty_label = None
  
  #def __init__(self, tree_id, init_term_id, *args, **kwargs):
    ##! personally, I think this is cobbled. Go to SQL join?
    #term_ids = TermTree.objects.filter(tree__exact=tree_id).values_list('term', flat=True)
    ##print('Term ids:')
    ##print(str(term_ids))
    #super().__init__(initial=init_term_id, queryset=Term.objects.filter(pk__in=list(term_ids)))

  #def label_from_instance(self, obj):
    ##! escape?
    #return obj.title

class AllTermSelectField(forms.ModelChoiceField):
  '''
  Select box containing terms from a taxonomy
  '''
  # When we know the choice of none is not possible
  #empty_label = None
  
  def __init__(self, *args, **kwargs):
    #! personally, I think this is cobbled. Go to SQL join?
    #root_terms = TermParent.objects.filter(parent__null=True)
    #term_ids = TermTree.objects.filter(taxonomy__exact=taxonomy_id).values_list('term', flat=True)
    #print('Term ids:')
    #print(str(term_ids))
    super().__init__(queryset=Term.objects.all())

  def label_from_instance(self, obj):
    #! escape?
    return obj.title
    
###############################################################

#class TermForm(forms.ModelForm):
  #tree = TaxonomySelectField()
  ##! how to get init_id in here? via. __init__()?
  #parent = TermSelectField(tree_id=1, init_term_id=3)

  #def __init__(self, *args, **kwargs):
    ##self._slug = kwargs.pop('pk')
    
    ##print('term form init............')
    ##print(str(kwargs))
    #super(TermForm, self).__init__(*args, **kwargs)
        
  #class Meta:
    #model=Term
    #fields = ['title', 'slug', 'weight']

    
#class TermAdmin(admin.ModelAdmin):
  ##fields.append(TaxonomySelectField(widget=forms.Textarea()))
  #prepopulated_fields = {"slug": ("title",)}
  #list_display = ['title', 'slug']
  #form = TermForm


  ##def __init__(self, *args, **kwargs):
    ##super(TermAdmin, self).__init__(*args, **kwargs)
    ##if hasattr(self, 'instance'):
    ##  self.fields['taxonomy'].initial = TaxonomySelectField()
    ##self.initial['books'] = self.instance.books.values_list('pk', flat=True)
    ##print('init:')
    ##print(str(self.fields))
  ## validate parentage is ok
  ##def clean_name(self):
    ## do something that validates your data
    ##return self.cleaned_data["name"]
      
  #def save_model(self, request, obj, form, change):
    #print(str(form.fields))
    #print(str(form.base_fields))
    #print(str(form.visible_fields))

    ##Select
    ##if (not change):
    ##TermTree(term=obj.id, taxonomy=obj.taxonomy)
    ##model = TermTree(term=obj.id, taxonomy=obj.taxonomy)  
    ##model.save()
    
    #print('saving model:')  
    ##super().save_model(request, obj, form, change)
        
    ##add the hierarchy
    #print('saving heirarchy:') 
    ## after save() so that id is populated from inserts
    ## should work for update and insert 
    #h = TermParent(term=obj.id, parent=obj.parent)  
    #h.save()

        
admin.site.register(Term)


##################################################


#class TaxonomyAdmin(admin.ModelAdmin):
#  prepopulated_fields = {"slug": ("title",)}
#  list_display = ['title', 'slug']
  
class TaxonomyAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}
    list_display = ['title', 'slug']
    
    def get_urls(self):
        from django.conf.urls import url
        urls = super(TaxonomyAdmin, self).get_urls()
        my_urls = [
            #url(r'^my_view/$', self.my_view),
            url(r'^wooby/$', self.admin_site.admin_view(self.changelist_view), name='taxonomy_taxonomy_changelist'),
        ]
        return my_urls + urls

    #def my_view(self, request):
        ## ...
        #context = dict(
           ## Include common variables for rendering the admin template.
           #self.admin_site.each_context(request),
           ## Anything else you want in the context...
           #key=value,
        #)
        #return TemplateResponse(request, "sometemplate.html", context)
        
admin.site.register(Tree, TaxonomyAdmin)


#####################################################



#class TermParentAdmin(admin.ModelAdmin):
  # Not working
  #raw_id_fields = ("term",)
  #form = TermTaxonomyForm
  #list_select_related = ('term', 'parent')

 #def get_form(self, request, obj=None, **kwargs):
 #       if request.user.is_superuser:
 #           kwargs['form'] = MySuperuserForm
 #       return super(MyModelAdmin, self).get_form(request, obj, **kwargs)
  
admin.site.register(TermParent)

######################################################


class TermTaxonomyForm(forms.ModelForm):
  taxonomy = TaxonomySelectField()
  term = AllTermSelectField()
  
  class Meta:
    model=TermTree
    fields = ['tree', 'term']

class TermTaxonomyAdmin(admin.ModelAdmin):
  # Not working
  #raw_id_fields = ("term",)
  form = TermTaxonomyForm
  list_select_related = ('term', 'tree')

 #def get_form(self, request, obj=None, **kwargs):
 #       if request.user.is_superuser:
 #           kwargs['form'] = MySuperuserForm
 #       return super(MyModelAdmin, self).get_form(request, obj, **kwargs)
  
admin.site.register(TermTree, TermTaxonomyAdmin)

########################################

admin.site.register(TermNode)
