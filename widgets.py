from django.conf import settings
from django.forms import Media, TextInput
from django.core.exceptions import ImproperlyConfigured



class IDTitleAutocompleteInput(TextInput):
    '''
    Widget for autocompleting a display via AJAX.
    
    Would usually be used with a field which can deliver the ajax_href, 
    for example, an IDTitleAutocompleteField.
    '''
    ##! not rendering!!!
    @property
    def media(self):
        css = {
            'all': ('taxonomy/css/plugin.css',)
        }
        extra = '' if settings.DEBUG else '.min'
        js = [
            'admin/js/vendor/jquery/jquery%s.js' % extra,
            'taxonomy/js/plugin.js',
            'taxonomy/js/jquery-ui%s.js' % extra,
        ]
        return Media(js=js, css=css)


    def __init__(self, ajax_href=None, attrs=None):
        self.ajax_href = ajax_href
        final_attrs = {
            'class': 'autocomplete-titled-id',
            'autocomplete': "off",
            'size': '10'
        }
        if attrs is not None:
            final_attrs.update(attrs)
        super().__init__(attrs=final_attrs)
        
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # delay setting of href to allow a field to poke in
        if (self.ajax_href is None):
            raise ImproperlyConfigured('no ajax_href defined')
            
        context['widget']['attrs'].update({'ajaxref': self.ajax_href})
        return context

