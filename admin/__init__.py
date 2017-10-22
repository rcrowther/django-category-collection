from django.contrib import admin

from ..models import Base, Term
from .admins import BaseAdmin, TermAdmin

admin.site.register(Base, BaseAdmin)
admin.site.register(Term, TermAdmin)
