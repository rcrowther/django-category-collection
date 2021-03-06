# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-24 05:49
from __future__ import unicode_literals

from django.db import migrations, models
import taxonomy.models


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0019_auto_20170908_1804'),
    ]

    operations = [
        migrations.CreateModel(
            name='TreeTerm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tree', models.IntegerField(db_index=True, help_text='A Tree associated with this Term.')),
                ('term', models.IntegerField(db_index=True, help_text='Term associated with a Tree.')),
            ],
        ),
        migrations.AddField(
            model_name='termnode',
            name='tree',
            field=models.IntegerField(db_index=True, default=29, help_text='A Tree associated with an element.'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='termnode',
            name='term',
            field=models.IntegerField(help_text='A Term associated with an element.', verbose_name=taxonomy.models.Term),
        ),
    ]
