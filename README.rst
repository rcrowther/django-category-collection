Django category collection
==========================

    **This module is deprecated**It is replaced by far more limited and Django-like https://github.com/rcrowther/django-taxonomy. The repository will be retained in case anyone is using it , and because it contains some useful code.

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
There are several ways to define a taxonomy structure. This app establishes 'bases'. Each base can contain several trees of 'terms'.

You can only attach data elements to terms, not the 'base'. If you would like a taxonomy where elements can be attached to the base, start a base then add a single term which will be the 'root term'. Build from there e.g. ::

    base = 'car categories'
    - Cars
    -- saloon 
    -- hatchback 
    -- sport
    ...
  
etc. now you can attach an unclassified car to the generic term 'cars'.

Requirements
------------
None. Not even 'django.contrib.admin'.

Install
-------
Put the code inside your project/emvironment. Then,

'settings.py', ::

    INSTALLED_APPS = [
        'taxonomy.apps.TaxonomyConfig',
        ...
    ]

Site-wide 'urls.py', ::

    urlpatterns = [
        url(r'^taxonomy/', include('taxonomy.urls')),
        ...
    ]

The wise app is humble, ::

    python manage.py taxonomy_uninstall -h

If you wish to avoid accidents, delete the folder 'management'.


The categories app has an admin interface, but it is compromised . See below.



Current state
-------------
'Draft'. I'm not a Python programmer, and am new to Django. On the other hand, this app is not 'ALPHA'; if used as recommended it can never destroy your data, by design. The API was, in part, introduced to give some confidence in stability.

Now wandering up Version 2. This is because the API has changed, not any notion of target aims (semantic versioning).


Fast start/want only to look/know what you want?
------------------------------------------------
Install (see up).

Start at http://127.0.0.1:8000/admin/taxonomy and build a base with some terms.
 
Look in taxonomy.api for methods. Probably, ::

    api.Taxonomy.term(term_pk)

Put this in a view, then render the results.


 
Admin
-----
The core models can be maintained through Django admin. You wil find a 'Bases' entry, and a non-functional 'Terms' entry. Start with 'Bases'.

The app uses a non-'admin' based set of forms and views for administration. The styling is similar to Django admin. However, the forms link in a different way, from overview lists to action, treating the app as a coherent whole. Start at http://127.0.0.1:8000/admin/taxonomy and work from there.


General Structure
------------------
Define a base. Put terms into the base and parent them with other terms, or at the bottom in \<root\>,:

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
To attach an element, ::

  Element.system.merge(term_pks, element_pk)  

To delete, ::

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

There is an issue; the Taxonomy app holds term data in one big table. Any forms displaying a choice from a foreign key will offer terms from every base. If you wish to limit term selection to one base, you will need to do some extra work (you may like to try one of the Field/Widget combinations below).

I havn't pursued this much, preferring to work on non-integrated admin. Foreign Keys will work well enough as they stand. Sometime...


Attaching elements without using a foreign field
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Django has multiple possibilities for forms and code. Here are the main solutions.

The below methods, except for the note about code, add a 'select' box to an admin form. You are not limited to admin, the same methods can add Taxonomy selection fields to other forms. 

As we will see further on, other more-scaleable widgets are available.



An admin form, fully broken out
+++++++++++++++++++++++++++++++
Your form is broken out because it is heavily customised for structure, maybe has extra fields. Add these ::
    
    # 1. import the methods and custom form field
    from taxonomy import element
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
            element.form_set_select(self, 'taxonomy_term', 32, instance)
    
    
Note that the two form additions need the 'base' value to be set. This may seem limiting but is typical Django procedure. This parameter must be set also in the next step.
    
Now we need to save and load the results. In ModelAdmin, :: 
    
    class ArticleAdmin(admin.ModelAdmin):
        form = ArticleForm
        ...
    
        def save_model(self, request, obj, form, change):
            super().save_model(request, obj, form, change)
            # 4. Save the connection (or disconnection) to a term
            element.save(form, 'taxonomy_term', 32, obj)
    
          
        def delete_model(request, obj):
            super().delete_model(request, obj)
            # 5. Tidy the taxonomy by deleting any connection to a term
            element.remove(32, obj)
  
Right, that's it. Instances of the Model (in this example, 'Article') can now be attached and detached from taxonomy terms. If either the term or the element is deleted, the connection will be automatically removed. The system is the same for any form using ModelAfmin or ModelForm.


ModelAdmin only
++++++++++++++++
You have an ModelAdmin, but no form, because you did some customization but nothing that altered the structure of the form. Do this, ::

    # 1. import this method (despite the capital letters, it's a method. But a class factory, which acts like, and returns, a class)
    from taxonomy.modeladmin import WithTaxonomyAdmin
    
        # 2. inherit from WithTaxonomyAdmin, not forms.ModelAdmin. The meta-constructor requires a base_pk
        class ArticleAdmin(WithTaxonomyAdmin(32)):
            # 3. (WithTaxonomyAdmin acts as ModelAdmin, so...) you must declare the field 'taxonomy_term', or the field will not appear
            fields = ('taxonomy_term', 'title', 'slug', 'summary', 'body', 'author')
  
Now this admin form will show a field where instances of the model can be attached and detached from taxonomy terms. 

This code is naturally DRY. It also behaves, for all other customisation, like a ModelAdmin form. Still, there is more... [TODO: not figured out if this can be done yet]


Another way, there is
++++++++++++++++++++++
This far, we have put a the options onto the element form itself. This seems intuitive and efficient. Mostly. But if your users pass much time categorising content, or categorise in bulk, then there is a different approach to the joining of elements to terms, which is to provide a seperate form (in truth, this only a start on the possibilities. Do you attach elements to multiple terms, or multiple terms to elements? How about one central form to rule them all? But, for now...).

The app contains a suggestion about how you could start. It may be good for some situations. The solution is as minimal as I could concieve. It currently uses two AJAXing HTML inputs (described down a bit).

Go into the app for the model you want to attach to a taxonomy, then to urls.py, then add, ::
    
    from taxonomy import element
    from .models import Birds
  
Birds is the name of the model; 'urls.py' often contains this import. Then add this to the urlpatterns, ::

    urlpatterns = [
        ...
    ] + element.get_urls(model=Birds, base_pk=12, navigation_links=[])
  
'Birds' is the name of the model, as imported. 'base_pk' identifies a taxonomy base. Ignore 'navigation_links', it's a rendering detail.

That's it. The only new URL you care about is at, ::

    birds/taxonomy/add-delete

where two auto-complete input boxes allow a user to connect and disconnect 'Birds' (in this case) from taxonomy base 12 (in this case). 


Fields and Widgets
~~~~~~~~~~~~~~~~~~
The code includes a special Field (and Widget), ::

    IDTitleAutocompleteField
    IDTitleAutocompleteInput

The field is fundamentally a numeric field, but displays text too. The widget puts the text and number in the same box, then strips the text on verification. This idea will not appeal to everyone, but is the most basic answer for the display of elements.

The Field is powered by a JQuery auto-completion widget. This needs an link and URL to gain data from. Data should be in JSON, a list of tuples (id, title). As a starter example, a suitable URL/JSON view is in the set provided for Taxonomy, which can deliver taxonomy terms to this Field/Widget. 

The field needs an AJAX URL, and there are a crazy number of ways of defining the URL within a form (the system is similar to the definition of the 'choice' attribute in selector fields). The ways I like are, if there is nothing dynamic about the URL, to declare on the field, ::

    id_title = IDTitleAutocompleteField(
      ajax_href='/taxonomy/term_titles/29',
      label='Element ID/Title', 
      help_text="Title of an element to be categorised."
      )

If the Field is dynamic, well, Django is not good at this. However, the 'init' trick works, and so does poking in the value (like 'choices', declarations at field level or after form building will override widget definitions) so, ::

        form = MyElementForm()
        form.fields['id_title'].widget.ajax_href = '/taxonomy/term_titles/1'

The Field/Widget has no default 'ajax_url'. If the property is unstated at the time of form building then the Field/Widget will throw an exception.

Second note; the Widget uses several bits of CSS and JS. So you will need to put a call to media into the template context, ::

    context = [
        media: form.media,
        ...
    ]

and place, ::

    {{ media }}

in template heads. Or the field will not react.


Displaying taxonomy information
--------------------------------
A taxonomy container can organise data internally. It can also display information to a user. This is a chance for all you front-end developers to show your skills. I'll show basics.

Remember, a taxonomy container can perform many tasks. It may model a family tree. It may organise collections of photographs. Or it may run a menu system.

Let's say the taxonomy runs a menu system (this is a chance to show some methods visually). Personally, if the menu system was simple, I'd not use a taxonomy---I'd put the navigation bar in a template. But if people need to change the menus, or the menu system becomes deep, or needs to be maintained by others, you may consider a taxonomy.

So you build a taxonomy, and the structure you have reflects the data you have. It may look like this,

.. figure:: https://raw.githubusercontent.com/rcrowther/django-category-collection/master/text/images/terms_in_a_base.png
    :width: 160 px
    :alt: breadcrumb screenshot
    :align: center
    

This taxonomy base has the id 7 (the url on the edit bar showed this).


Displaying children/parents (a navigation bar)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
And you have a view for the front page. Add code like this, ::

    def front_page(request): 
        article = # get this data by your own method
        ...
        
        # 1. Get the immdiate children of the taxonomy base. This 
        # is a shortcut-from a Base, children() will get terms at root. 
        bapi = api.Taxonomy.slug('site-structure') 
        children = bapi.children()
    
        # 2. Render the child data in some way. For this example, I only
        # use the term title, and and assume some code in tmpl_li_link()
        # does the rendering, not a template.
        b = []
        for c in children:
            b.append(tmpl_li_link('/' + c.title, c.title))
            
        # 3. Add the rendered code to the template context in 'nav'.
        nav = {}      
        nav['links'] = mark_safe(''.join(b))
        return render(request, 'test.html', {'nav': nav, 'article': article})

Now we adjust the template. We have only rendered the children, and we'd like a 'home' link, so we start the render with a fixed 'home' link. That one will not change. After that, the links made from children, ::

        <ul>
          <li><a class="home" href="/">Home</a></li>{{ nav.links }}
        </ul>

And if we render with some CSS, this might appear,

.. figure:: https://raw.githubusercontent.com/rcrowther/django-category-collection/master/text/images/taxonomy_children.png
    :width: 160 px
    :alt: breadcrumb screenshot
    :align: center

    It's a nav bar.
   
   
As I said above, for a small site, I wouldn't bother. Still, taxonomy control has advantages. If this little magazine-style site takes off, they may find their data changing. For example; the owners are not keen for people to contact them, as they have a lot going on. And a new person arrived who wanted to cover sport. So we go to the taxonomy admin (not the template), add some weight to the 'contact' term, then add a new term/category for 'sport'. Next render, we get this,

.. figure:: https://raw.githubusercontent.com/rcrowther/django-category-collection/master/text/images/taxonomy_children_adjusted.png
    :width: 160 px
    :alt: breadcrumb screenshot
    :align: center

    New layout? 5 secs.
   
You can use 'term_parents(base_pk, term_pk)' to return the parents of a term. This is  good for titles and the like, telling a user where they came from, or are under. Note the plural---if you are using a multiple-parent taxonomy, the method may return several parents.


Displaying paths (breadcrumb trails)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
There are many methods in the API. TermAPI.term_ancestor_paths() gets the paths back from a term to the root. The code is nearly the same as the last code, but note the use of an index for '0', ::

    path = api.term_ancestor_paths(7, 141)[0]
    
    b = []
    for c in path:
        b.append(tmpl_li_link('/' + c.title, c.title))
    nav = {}      
    nav['links'] = mark_safe(''.join(b))
    return render(request, 'test.html', {'nav': nav, 'article': paper})

Why do we need to get path[0]?  If this was a multiple parent taxonomy, there would be many possible paths back to root (think about it...). term_ancestor_paths() will return them all. Handled well, this could lead to some innovative displays, or it could be bewildering. But we are looking at a single-parent taxonomy. There is only one path back to root, and we can safely assume that will be index [0].

The result, with the fixed home link and some new CSS, might look like this,

.. figure:: https://raw.githubusercontent.com/rcrowther/django-category-collection/master/text/images/breadcrumb.png
    :width: 160 px
    :alt: breadcrumb screenshot
    :align: center

    You know it as a 'breadcrumb'

Yes, it is what web-designers call a 'breadcrumb trail'. There are also intruiging possibilities in a complementary method, term_descendant_paths(). This can show a user where they can go next. But be careful; the method will return multiple paths, even in a single-parent taxonomy.

And, by the way, that tree which the administration uses is available too, ::

    def terms_flat_tree(base_pk, parent_pk=ROOT, max_depth=FULL_DEPTH):

it returns a list of ordered term data from cache, with a depth attribute attached. The list elements are a named tuple, this, ::

    TermFTData = namedtuple('TermFTData', ['pk', 'title', 'slug', 'description', 'depth'])
    
I see possibilities...



Displaying a tree
~~~~~~~~~~~~~~~~~
The code which builds the 'select widget' data is in the API, ::

    api.BaseAPI.flat_tree(self, parent_pk=ROOT, max_depth=FULL_DEPTH)

It's rare to see on websites but many displays are possible. The 'inlinetemplates' module provides a class TreeRender. This is only suitable for very small taxonomies but nice to look at and efficient. Assume a Base 'grasses' has been built, and a view/template 'article' exists in which we can put the results. Put this in the view, ::

    from django.utils.safestring import mark_safe
    from django.utils import html
    from taxonomy import api
    from taxonomy.inlinetemplates import TreeRender

    def get_title(pk):
        return html.escape(api.Taxonomy.term(pk).title)
    ...
    # 1. Get the tree
    bapi = api.Taxonomy.slug('angiosperms-flowering-plants')
    t = bapi.flat_tree()
    
    # get the renderer, then adjust a few of the display parameters 
    tr = TreeRender()
    tr.beam_style = 'stroke:rgb(0,220,126);stroke-width:4;'
    tr.stem_style = 'stroke:rgb(0,220,126);stroke-width:2;'

    #3. Rend (needs a callback for data delivery into the template)
    tree = tr.rend_default_horizontal(t, 200, 14, get_title)
    
    #4. Deliver into the template
    article.body = mark_safe(tree)
    return render(request, 'article.html', {'article': article})

The only verbose part is the callback which supplies the data.

This code renders as,

.. figure:: https://raw.githubusercontent.com/rcrowther/django-category-collection/master/text/images/base_render.png
    :width: 160 px
    :alt: 2D render of a base
    :align: center
     
The result is an active DOM-based webpage. An override of TreeRender, AnchorTreeRender, will deliver clickable links. You may like to know also that this example is lightweight on the coder(no libraries), server (microseconds), and the user(stock HTML, no Javascript, no CSS). But others can follow this path and go crazy.



Extra
-----
The API
~~~~~~~
The API is class-based (or, in places, object-based), ::
    
    TermAPI(term_pk)
    BaseAPI(base_pk)
    ElementAPI(element_pk)
    Taxonomy
  
Then start using the methods.
 
The class code tries to do the right thing by the rest of the code. It sometimes lazy instanciates, cleans up after database changes, that kind of action.

Notes;
+ You may find methods in places you do not expect. To add a new term, look in BaseAPI. A new term goes into a Base,
+ If you want the information from a Term or Base, look at api.Taxonomy.term() and api.Taxonomy.base(). 



Code organisation
~~~~~~~~~~~~~~~~~
Taxonomy collections are complex beyond their simple models.
 
Only work with the Models if you need to repair or want to play. The models keep '.objects' as the primary model manager. The methods can damage the collections; make orphans of links and create circular dependencies. Beyond, each Model adds a second manager called '.system'. These managers contain methods which will maintain the integrity of the collections.

Next is a module called 'cache'. This is not Django cache, it is maintained by the app to speed some of the actions and provide interesting functionality. It's sensitive.

The 'api' module pulls these parts together in a facade. This is where you would look for methods to use in your code. 

You will not find much in 'views.py' besides JSON rendering. 'taxadmin.py' contains the admin gear, 'modeladmin.py' a couple of constructions for ModelAdmin, and 'element.py' contains the various forms/fields/widgets for handling element association/disassociation.


A note on implementation
~~~~~~~~~~~~~~~~~~~~~~~~
This is one of my first efforts in Django. It has caused me trouble. The form documentation was not helpful, so I hand-built the admin from Form, not ModelForm, classes. I resent being pushed into this, even if I feel the final implementation is better that way. The data modelling caused me similar problems and has, in several places, abandoned relational Fields for SQL. Again, I prefer it that way, but am unhappy about needing to do this in the first instance.


A comparison of 'Django category collection' and 'django-categories'
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
In comparison, the theory behind this project will be inelegant at discovering data elements from multiple terms. The action is possible, but not of great interest and has not been implemented (yet). Also, this project caches all data from terms/categories, and so may not scale well to many terms. Before you implement the Dewey_ reference system, please run tests.

However, this implementation of a category collection has advantages (as all differing implementations will). The app is nearly self-contained. It's storage models are plain and few, making backup and salvage simple---salvage can be managed through Django admin. The view code is twisty in places, but can derive really useful data from the category trees. Without AJAX or whatever, the core methods are sophisticated. And finally, the container in this app has a Django/Pythonlike interface.

.. _Dewey: https://en.wikipedia.org/wiki/Dewey_Decimal_Classification

