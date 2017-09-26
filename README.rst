Django category collection
==========================
For Django, the Python-coded Web development framework.

A collection modelling categories (sometimes known as 'taxonomies').


Alternatives
------------

https://djangopackages.org/packages/p/django-categories/
https://github.com/callowayproject/django-categories

    This project is mature with many commits. It uses the MPTT technique of data description, so is a fundamentally different implementation to the project here. An MPTT implementation will be good at isolating trees of categories, and gathering data elements from multiple categories/terms (e.g. you want all 'cars', even if the categorisation of 'cars' include many sub-categories). For more detail see the comparison at the end of this page.


Names/nomenclature
------------------
The app is called 'categories'. But the app is called, and the URLs are rooted, at 'taxonomy'. One set of categories is called a 'base'. A 'category' within a base is called a 'term'. Data attached to a tree of terms, 'categorised data', are called 'elements'.


Data layout in the taxonomy
---------------------------
There are several ways to define a taxonomy structure. This taxonomy establishes 'bases'. Each base can contain several trees of 'terms'.

You can only attach data elements to terms, not the 'base'. If you would like a taxonomy where elements can be attached to the base, start a base then add a single term which will be the 'root term'. Build from there e.g.::

    base = 'car categories'
    - Cars
    -- saloon 
    -- hatchback 
    -- sport
    ...
  
etc. now you can attach an unclassified car to the generic term 'cars'.


Admin
-----
The core models can be maintained through Django admin, but the module includes a non-'admin' based set of forms and views for administration.

These forms are not protected by passwords, nor will be ever ('we are all grown-ups here'). Enable, disable, and protect the URLs as you wish.

The base look of the admin views and forms is similar to Django admin. However, the forms link in a different way, from overview lists to action, treating the app as a coherent whole. Start at http://127.0.0.1:8000/taxonomy and work from there.


General Structure
------------------
Define a base. Put terms into the base and parent them with other terms, or at the bottom in \<root\>,::

    base = Fabrics
    - Corduroy 
    - Denim  
    - Linen 
    -- Untreated
    - Cotton
    -- Herringbone 
    -- Dye-printed
    --- Colourfast
    --- Speciality
    -- Rough 
    - Felt

etc.

Now add elements to the terms in the trees. 


To attach elements to terms
---------------------------
Many possibilities here. But, first, you may not use a taxonomy to classify user-visual content at all. You may use one to classify downloadable files. Or your app may not offer a conventional admin interface. You need to know about,

Using code
~~~~~~~~~~
To attach an element,::

  Element.system.merge(term_pks, element_pk)  

To delete,::

  Element.system.delete(base_pk, element_pks):

Ok, let's go on to using Django models as elements. 


To attach other models to terms
-------------------------------
To store elements in the taxonomy you do not need to modify the models of the element to be stored. All that needs to be done is to work with the id/pk of the element data. 

Of course, there is nothing to stop you adding a Foreign field to a model which refers to taxonomy terms. This will make finding the term a model is attached to very easy. But if you need further data such as term parents, and you usually will, most advantages of this shortcut will be lost. 

In general, I don't think a categorisation system should intrude on data, especially in a web environment. Perhaps at some point I will add this feature? But a Python list makes no requirement on it's contents. 

When no foreign field is used, the connection between element models and the taxonomy collection is loose. If you use this approach, it's up to you, the coder, to keep the keys you store on a tree unique. The app makes a minimal attempt at keeping the database consistent by refusing duplicate keys on a term, but that is all.


Using a Foreign Field in the element model, and Django Admin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
One good reason for using a Foreign Field in element Models is because the taxonomy will integrate seamlessly into Django Admin. All the normal methods for modification and display will work. 

There is an issue; the Taxonomy app holds term data in one big table. Any forms displaying a choice from a fereign key will offer terms from every base. If you wish to limit term selection to one base, you will need to do some extra work (you may like to try one of the Field/Widget combinations below).

I havn't pursued this much, preferring to work on non-integrated admin. Foreign Keys will work well enough as they stand. Sometime...


Attaching elements without using a foreign field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Django has multiple possibilities for forms and code. Here are the main solutions.

The below methods, except for the note about code, add a 'select' box to an admin form. You are not limited to admin, the same methods can add Taxonomy selection fields to other forms. 

As we will see further on, other more scaleable widgets are available.

For GUI forms, use the form at

taxonomy/term/(?P<term_pk>\d+)/element/merge/





An admin form, fully broken out
+++++++++++++++++++++++++++++++
Your form is broken out because it is heavily customised for structure, maybe has extra fields. Add these::
    
    # 1. import the methods and custom form field
    from taxonomy.views import form_set_select, element_save, element_remove
    from taxonomy.fields import TaxonomyTermField
    
    class ArticleForm(ModelForm):
        # 2. add the extra field to the form (this will not save to the Model database table, is here to choose a term)
        taxonomy_term = TaxonomyTermField()
    
            
        def __init__(self, data=None, files=None, auto_id='id_%s', prefix=None,
                     initial=None, error_class=ErrorList, label_suffix=None,
                     empty_permitted=False, instance=None, use_required_attribute=None):
            super().__init__(data, files, auto_id, prefix,
                     initial, error_class, label_suffix,
                     empty_permitted, instance, use_required_attribute)
            
            # 3. Set allowable choices
            form_set_select(self, 'taxonomy_term', 32, instance)
    
    
Note that the two form additions need the 'base' value to be set. This may seem limiting but is typical Django procedure. This parameter must be set also in the next step.
    
Now we need to save and load the results. In ModelAdmin,::    
    
    class ArticleAdmin(admin.ModelAdmin):
        form = ArticleForm
        ...
    
        def save_model(self, request, obj, form, change):
            super().save_model(request, obj, form, change)
            # 4. Save the connection (or disconnection) to a term
            element_save(form, 'taxonomy_term', 32, obj)
    
          
        def delete_model(request, obj):
            super().delete_model(request, obj)
            # 5. Tidy the taxonomy by deleting any connection to a term
            element_remove(32, obj)
  
Right, that's it. Instances of the Model (in this example, 'Article') can now be attached and detached from taxonomy terms. If either the term or the element is deleted, the connection will be automatically removed. The system is the same for any form using ModelAfmin or ModelForm.


ModelAdmin  only
++++++++++++++++
You have an ModelAdmin, but no form, because you did some customization but nothing that altered the structure of the form. Do this,

# 1. import this method (despite the capital letters, it's a method. But a class factory, which acts like, and returns, a class)
from taxonomy.modeladmin import WithTaxonomyAdmin

    # 2. inherit from WithTaxonomyAdmin, not forms.ModelAdmin. The meta-constructor requires a base_pk
    class ArticleAdmin(WithTaxonomyAdmin(32)):
        # 3. (WithTaxonomyAdmin acts as ModelAdmin, so...) you must declare the field 'taxonomy_term', or the field will not appear
        fields = ('taxonomy_term', 'title', 'slug', 'summary', 'body', 'author')

Now this admin form will show a field where instances of the model can be attached and detached from taxonomy terms. 

This code is naturally DRY. It also behaves, for all other customisation, like a ModelAdmin form. Still, there is more... [TODO: not figured out if this can be done yet]


Fields and Widgets
~~~~~~~~~~~~~~~~~~
The code includes a special Field (and Widget),::

    IDTitleAutocompleteField
    IDTitleAutocompleteInput

The field is fundamentally a numeric field, but displays text too. The widget puts the text and number in the same box, then strips the text on verification. This idea will not appeal to everyone, but is the most basic answer for the display of elements.

The Field is powered by a JQuery auto-completion widget. This needs an link and URL to gain data from. Data should be in JSON, a list of tuples (id, title). As a starter example, a suitable URL/JSON view is in the set provided for Taxonomy, which can deliver taxonomy terms to this Field/Widget. 

The field needs an AJAX URL, and there are a crazy number of ways of defining the URL within a form (the system is similar to the definition of the 'choice' attribute in selector fields). The ways I like are, if there is nothing dynamic about the URL, to declare on the field,::

    id_title = IDTitleAutocompleteField(
      ajax_href='/taxonomy/term_titles/29',
      label='Element ID/Title', 
      help_text="Title of an element to be categorised."
      )

If the Field is dynamic, well, Django is not good at this. However, the 'init' trick works, and so does poking in the value (like 'choices', declarations at field level or after form building will override widget definitions) so,::

        form = MyElementForm()
        form.fields['id_title'].widget.ajax_href = '/taxonomy/term_titles/1'

The Field/Widget has no default 'ajax_url'. If the property is unstated at the time of form building then the Field/Widget will throw an exception.

Second note: the Widget uses several bits of CSS and JS. So you will need to put a call to media into the template context,::

    context = [
        media: form.media,
        ...
    ]

and place,::

    {{ media }}

in template heads. Or the field will not react.


TODOs
-----
SQL and data structure needs a review.

A note on implementation
------------------------
This is one of my first efforts in Django. It has caused me trouble. The form documentation was not helpful, so I hand-built the admin from Form, not ModelForm, classes. I resent being pushed into this, even if I feel the final implementation is better that way. The data modelling caused me similar problems and has, in several places, abandoned relational Fields for SQL. Again, I prefer it that way, but am unhappy about needing to do this in the first instance.


A comparison of 'Django category collection' and 'django-categories'
---------------------------------------------------------------------
In comparison, the theory behind this project will be inelegant at discovering data elements from multiple terms. The action is possible, but not of great interest and has not been implemented (yet). Also, this project caches all data from terms/categories, and so may not scale well to many terms. Before you implement the Dewey_ reference system, please run tests.

However, this implementation of a category collection has advantages (as all differing implementations will). The app is nearly self-contained. It's storage models are plain and few, making backup and salvage simple---salvage can be managed through Django admin. The view code is twisty in places, but can derive really useful data from the category trees. Without AJAX or whatever, the core methods are sophisticated. And finally, the container in this app has a Pythonlike interface.

.. _Dewey: https://en.wikipedia.org/wiki/Dewey_Decimal_Classification

