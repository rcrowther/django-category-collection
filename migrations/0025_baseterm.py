# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-24 12:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0024_auto_20170924_1145'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaseTerm',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('base', models.IntegerField(db_index=True, help_text='Base associated with a Term.')),
                ('term', models.IntegerField(db_index=True, help_text='Term associated with a Base')),
            ],
        ),
    ]
