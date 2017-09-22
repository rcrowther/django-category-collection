Django category collection
==========================
For Django, the Python-coded Web development framework.

A collection modelling categories (sometimes known as 'taxonomies'.


Alternatives
------------

https://djangopackages.org/packages/p/django-categories/
https://github.com/callowayproject/django-categories

    This project is mature with many commits. It uses the MPTT technique of data description, so is a fundamentally different implementation to the project here. Ab MPTT implementation will be good at isolating trees of categories, and gathering data elements from multiple categories/terms (e.g. you want all 'cars', even if the categorisation of 'cars' include many sub-categories). For more detail see the comparison at the end of this page.


Names/nomenclature
------------------
The app is called 'categories'. But the URLs are currently rooted at 'taxonomy'. One set of categories is called a 'tree'. A 'category' within a tree is called a 'term'. Data attached to a tree, 'categorised data', are called 'elements'.

Admin
-----
The core models can be maintained through Django admin, but the module includes a non-'admin' based set of forms and views for administration.

These forms are not protected by passwords, nor will be ever ('we are all grown-ups here'). Enable, disable, and protect the URLs as you wish.

The base look of the admin views and forms is similar to Django admin. However, the forms link in a different way, from overview lists to action, treating the app as a coherent whole. Start at http://127.0.0.1:8000/taxonomy and work from there.


General Structure
------------------
Define trees. Put terms into trees and parent them with other terms or \<root\>. 

Fabrics
Cord Denim  Linen Rough Cotton Herringbone Dye-printed Felt

etc.

Add elements to trees. 


On the attachment of elements to terms
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
To store elements in the taxonomy you do not need to modify the models of the element to be stored. All that needs to be done is to work with the id/pk of the models. 

Of course, there is nothing to stop you adding a Foreign field to a model which refers to taxonomy terms. This will make finding the term a model is in very easy. But as soon as you need further data such as parents, and you usually will, most advantage of this shortcut will be lost. 

In general, I don't think a categorisation system should intrude on data Models, especially in a web environment. Perhaps at some point I will add this feature? But a Python list makes no requirement on it's contents. 

This makes the connection between element models and the taxonomy collection loose. It's up to you, the coder, to keep the keys you store on a tree unique. The app makes a minimal attempt at keeping the database consistent by refusing duplicate keys on a term, but that is all.


To attach an element in code,::

  TermNode.system.merge(term_pk, element_id)  

For GUI forms, use the form at

taxonomy/term/(?P<term_pk>\d+)/element/merge/


Using a Foreign Field in the element model, and Django Admin
++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
One good reason for using a Foreign Field in element Models is because the taxonomy will integrate seamlessly into Django Admin. All the normal methods for modification and display will work. 

There is one issue; Taxonomy terms are held in one big table, so terms will be displayed from every tree. If you wish to limit term selection to one tree, you will need to do some extra work (you may like to try one of the Field/Widget combinations below).

I havn't pursued this much, preferring to work on non-integrated admin. Foreign Keys will work well enough as they stand. Sometime...



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
In comparison, the theory behind this project will be inelegant at discovering data elements from multiple terms. The action is possible, but not of great interest and has not been implemented (yet). Also, this project caches all data from terms/categories, and so may not scale well to many terms. Please run tests before you implement the Dewey_ reference system.

However, this implementation of a category collection has advantages (as all differing implementations will). The app is nearly self-contained. It's storage models are plain and few, making backup and salvage simple---salvage can be managed through Django admin. The view code is twisty in places, but can derive really useful data from the category trees. Without AJAX or whatever, even the core methods are sophisticated. And finally, this app has a Pythonlike interface.

.. _Dewey: https://en.wikipedia.org/wiki/Dewey_Decimal_Classification

