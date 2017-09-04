# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-04 20:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0009_auto_20170904_1959'),
    ]

    operations = [
        migrations.AlterField(
            model_name='termparent',
            name='parent',
            field=models.IntegerField(db_index=True, help_text='Term parent for another term, or null for root (connection to self forbidden)', null=True),
        ),
        migrations.AlterField(
            model_name='termparent',
            name='term',
            field=models.IntegerField(db_index=True, help_text='Term to connect to another Term.'),
        ),
    ]
