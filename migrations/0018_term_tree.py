# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-09-08 17:37
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('taxonomy', '0017_auto_20170905_1803'),
    ]

    operations = [
        migrations.AddField(
            model_name='term',
            name='tree',
            field=models.IntegerField(db_index=True, default=1, help_text='A Tree associated with this Term.'),
            preserve_default=False,
        ),
    ]
