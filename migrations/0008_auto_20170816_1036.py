# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-16 10:36
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0007_auto_20170816_1009'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='TaxonomyTerm',
            new_name='TermTaxonomy',
        ),
    ]