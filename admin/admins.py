from django.contrib import admin
from django.conf.urls import url
from django.shortcuts import render
from django.forms import ModelForm
from django import forms
from django.urls import reverse
from django.contrib import messages
import os
from django.conf import settings
from ..models import Base, Term, BaseTerm, TermParent, Element
from .taxadmin import (TermListView, BaseListView, 
    base_add, base_edit, base_delete,
    base_to_singleparent,
    term_add, term_edit, term_delete
    )



class TermAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        new_urls = [
            url(r'^(?P<term_pk>\d+)/edit/$', term_edit, name='taxonomy_term_change'),
            url(r'^(?P<term_pk>\d+)/delete/$', term_delete, name='taxonomy_term_delete'),
        ]
        #print (str(new_urls))
        return new_urls
        
class BaseAdmin(admin.ModelAdmin):
    def get_urls(self):
        urls = super().get_urls()
        new_urls = [
          url(r'^$',  BaseListView.as_view(), name='taxonomy_base_changelist'),
          url(r'^add/$', base_add, name='taxonomy_base_add'),
          url(r'^(?P<base_pk>\d+)/edit/$', base_edit, name='taxonomy_base_change'),
          url(r'^(?P<base_pk>\d+)/delete/$', base_delete, name='taxonomy_base_delete'),
          url(r'^(?P<base_pk>\d+)/tosingleparent/$', base_to_singleparent, name='taxonomy_base_tosingleparent'),
          # terms
          url(r'^(?P<base_pk>\d+)/term/list/$', TermListView.as_view(), name='taxonomy_term_changelist'),
          url(r'^(?P<base_pk>\d+)/term/add/$', term_add, name='taxonomy_term_add'),
        ]
        #print (str(new_urls))
        return new_urls 
