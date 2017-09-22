Django category collection
==========================
For Django, the Python-coded Web development framework.

A collection modelling categories (sometimes known as 'taxonomies'.


Alternatives
------------

https://djangopackages.org/packages/p/django-categories/
https://github.com/callowayproject/django-categories

    This project is mature with many commits. It uses the MPTT technique of data description, so is a fundamentally different implementation to the project here. The theory behind the project will be good at isolating trees of categories, and gathering data elements from multiple categories/terms (e.g. you want all 'cars', even if the categorisation of 'cars' include many sub-categories). 

Names/nomenclature
------------------
The app is called 'categories'. But the URLs are currently rooted at 'taxonomy'. One set of categories is called a 'tree'. A 'category' within a tree is called a 'term'. 

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
An important feature of this app is that the method of storing elements is to attach an id/pk. Model instances added to the terms do not require a field in the model. In code,::

  TermNode.system.merge(term_pk, element_id)  

For a handbuild, use the form at

taxonomy/term/(?P<term_pk>\d+)/element/merge/

I don't think a categorisation system should intrude on data Models, especially in a web environment. Perhaps at some point I will add this feature? But a Python list makes no requirement on it's contents. It's up to you to keep the keys you store on a tree unique (the module makes a minimal attempt at keeping the database consistent by refusing duplicate keys on a term, but that is all).


Fields and Widgets
~~~~~~~~~~~~~~~~~~
The code includes a special Field (and Widget),::

    IDTitleAutocompleteField
    IDTitleAutocompleteInput

The field is fundamentally a numeric field, but displays text too. The widget puts the text and number in the same box, then strips the text on verification. This will not be an idea to appeal to everyone, but is the most basic answer to displaying of nodes.

The Field is powered by a JQuery auto-completion widget. This needs an link and URL to gain data from. Data should be in JSON, a list of tuple (id, title). A suitable URL is in the basic set provided for Taxonomy, which delivers taxonomy terms via the same auto-completion widget. 

The field needs an AJAX URL, and there are a crazy number of ways to do that. Very like 'choice' in selector fields. The ways I like are, if there is nothing dynamic about the URL, to declare on the field,::

    title = IDTitleAutocompleteField(
      ajax_href='/taxonomy/term_titles/29',
      label='Element ID/Title', 
      help_text="Title of an element to be categorised."
      )

If the Field is dynamic, well, Django is not good at this. However, the 'init' trick works, and so does poking in the value (like 'choices', declarations at field level or subsequent to building will override widget definitions) so,::

        f.fields['title'].widget.ajax_href = '/taxonomy/term_titles/1'

If the 'ajax_href' property is unstated then the Field/Widget will throw an exception; the field has no default.

Second note: the field uses several bits of CSS and JS. So you will need to put call media into the template context,::

    context = [
        media: form.media,
        ...
    ]

and place,::

    {{ media }}

in the template head. Or the field will not react.

TODOs
-----
SQL and data structure needs a review.

A note on implementation
------------------------
This is one of my first efforts in Django. It has caused me trouble. The form documentation was not helpful, so I hand-built the admin from Form, not ModelForm, classes. I resent being pushed into this, even if I feel the final implementation is better that way. The data modelling caused me similar problems and has, in several places, abandoned relational Fields for SQL. Again, I prefer it that way, but am unhappy about needing to do this in the first instance.


A comparison of 'Django category collection' and 'django-categories'
---------------------------------------------------------------------
In comparison, the theory behind this project will be inelegant at discovering data elements from multiple terms. The action is possible, but not of great interest and has not yet been implemented. Also, this project caches all data from terms/categories, and so may not scale well to many terms. Please run tests before you implement the Dewey_ reference system.

However, this implementation of a category collection has advantages (as all differing implementations will). The app is nearly self-contained. It's storage models are plain and few, making backup and salvage simple---salvage can be managed through Django admin. The view code is twisty in places, but can derive really useful data from the category trees. Without AJAX or whatever, even the core methods are sophisticated. And finally, this app has a Pythonlike interface.

.. _Dewey: https://en.wikipedia.org/wiki/Dewey_Decimal_Classification

