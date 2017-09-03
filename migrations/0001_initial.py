# -*- coding: utf-8 -*-
# Generated by Django 1.11.4 on 2017-08-09 22:13
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Node',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Limited to 64 characters.', max_length=64)),
                ('parent', models.ForeignKey(blank=True, help_text='Connect to another node, or null.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', related_query_name='children', to='taxonomy.Node')),
            ],
        ),
    ]