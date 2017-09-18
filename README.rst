Django category collection
==========================
For Django, the Python-coded Web development framework.

A collection modelling categories (sometimes known as 'taxonomies'.


Alternatives
------------

https://djangopackages.org/packages/p/django-categories/
https://github.com/callowayproject/django-categories

    This project is mature with many commits. It uses the MPTT technique of data description, so is a fundamentally different implementation to this project. The theory behind the project will be good at isolating trees of categories, and gathering data elements from multiple categories/terms (e.g. you want all 'cars', even if the categorisation of 'cars' include many sub-categories). 

Names/nomenclature
------------------
The app is called 'categories'. But the URLs are currently rooted at 'taxonomy'. One set of categories is called a 'tree'. A 'category' within a tree is called a 'term'. 

Admin
-----
The core models can be maintained through Django admin, but the module includes a non-'admin' based set of forms and views for administration.

These forms are not protected by passwords, nor ever will be ('we are all grown-ups here'). Enable, disable, and protect the URLs as you wish.

The base look of the admin views and forms is similar to Django admin. However, the forms link in a very different way, from overview lists to action, treating the app as a coherent whole. Start at http://127.0.0.1:8000/taxonomy and work from there.


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

I don't think a categorisation system should be intruding on data Models, especially in a web environment. Perhaps at some point I will add this feature? But a Python list makes no requirement on it's contents. It's up to you to keep the keys you store on a tree unique (the module makes a minimal attempt at keeping the database consistent by refusing to duplicate keys on a term, but that is all).



TODOs
-----
SQL and data structure needs a review.

A note on implementation
------------------------
This is one of my first efforts in Django. It has caused me trouble. The form documentation was not helpful, so I hand-built the admin from Form, not ModelForm. I resent being pushed into this, even if I feel the final implementation is better that way. The data modelling caused me similar problems and has, in several places, abandoned relational Fields for simple SQL. Again, I prefer it that way, but am unhappy about needing to do this in the first instance.


A comparison of 'Django category collection' and 'django-categories'
---------------------------------------------------------------------
In comparison, the theory behind this project will be inelegant at discovering data elements from multiple terms. The action is possible, but not of great interest and has not yet been implemented. Also, this project caches all data from terms/categories, and so may not scale well to many terms. Please run tests before you implement the Dewey_ reference system.

However, this implementation of a category collection has advantages (as all differing implementations will). The app is nearly self-contained. It's storage models are plain and few, making backup and salvage simple---salvage can be managed through Django admin. The view code is twisty in places, but can derive really useful data from the category trees. Without AJAX or whatever, even the core methods are sophisticated. And finally, this app  has a Pythonlike interface.

.. _Dewey: https://en.wikipedia.org/wiki/Dewey_Decimal_Classification

