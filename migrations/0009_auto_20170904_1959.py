# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-04 19:59
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0008_auto_20170816_1036'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='TermTree',
            new_name='TermParent',
        ),
    ]
