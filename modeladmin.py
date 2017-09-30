from django.contrib.admin import ModelAdmin
from .fields import TaxonomyTermField
#from .element import form_set_select, element_save, element_remove
from taxonomy import element

#! could move to element module?
from django.forms import ModelForm

def WithTaxonomyForm(model1, base_pk, *args, **kwargs):
    class WithTaxonomyForm(ModelForm):
        taxonomy_term = TaxonomyTermField()
        class Meta:
            model = model1
            #fields = fields1
            fields = ['taxonomy_term']
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            element.form_set_select(self, 'taxonomy_term', base_pk, kwargs.get('instance'))   
    return WithTaxonomyForm
    
def WithTaxonomyAdmin(base_pk):
    class WithTaxonomyAdmin(ModelAdmin):
        def __init__(self, model, admin_site):
            super().__init__(model, admin_site)
            self.form = WithTaxonomyForm(model, base_pk)
        def save_model(self, request, obj, form, change):
            super().save_model(request, obj, form, change)
            element.save(form, 'taxonomy_term', base_pk, obj)
        def delete_model(self, request, obj):
            element.remove(base_pk, obj)
            super().delete_model(request, obj)
    return WithTaxonomyAdmin
